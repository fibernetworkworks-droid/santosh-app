"""A software bill of materials read for what ships inside: CycloneDX JSON or SPDX JSON (from syft, cdxgen, trivy, the GitHub
dependency graph export). Components counted by ecosystem and licence family (permissive, weak copyleft, strong copyleft, unknown);
licences against her own allow and deny lists; components with no licence, no version or no package URL; the same package at several
versions; and the components with no supplier. Licence families are a guide, not legal advice - whether a licence obliges you
depends on how the software is shipped."""
from __future__ import annotations

import json
import re
from typing import Any

from .common import DsoInputError, finder, finish


class SbomError(DsoInputError):
    pass


STRONG = re.compile(r"^(A?GPL|SSPL|OSL|RPL|Sleepycat|CC-BY-SA|EUPL|CPAL)", re.I)
WEAK = re.compile(r"^(LGPL|MPL|EPL|CDDL|CPL|Ms-RL|APSL|ErlPL)", re.I)
PERMISSIVE = re.compile(r"^(MIT|BSD|Apache|ISC|Zlib|Unlicense|0BSD|CC0|Python|PSF|BSL-1\.0|Boost|WTFPL|X11|NCSA|PostgreSQL|Artistic|BlueOak|UPL|HPND|curl|OpenSSL|Unicode)", re.I)
NOASSERT = {"", "noassertion", "none", "unknown", "other", "see license", "unlicensed"}


def family(lic: str) -> str:
    s = str(lic or "").strip()
    if s.lower() in NOASSERT:
        return "unknown"
    parts = [p.strip("() ") for p in re.split(r"\s+(?:OR|AND|WITH)\s+", s, flags=re.I) if p.strip("() ")]
    if " OR " in s.upper() and any(PERMISSIVE.match(p) for p in parts):
        return "permissive"   # a choice that includes a permissive licence
    fams = ["strong" if STRONG.match(p) else "weak" if WEAK.match(p) else "permissive" if PERMISSIVE.match(p) else "unknown" for p in parts]
    for f in ("strong", "weak", "unknown"):
        if f in fams:
            return f
    return "permissive" if fams else "unknown"


def _cdx_lic(c: dict[str, Any]) -> str:
    out = []
    for x in c.get("licenses") or []:
        if "expression" in x:
            out.append(str(x["expression"]))
        lic = x.get("license") or {}
        if lic.get("id") or lic.get("name"):
            out.append(str(lic.get("id") or lic.get("name")))
    return " AND ".join(out)


def _parse(d: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    rows = []
    if d.get("bomFormat") == "CycloneDX" or "components" in d:
        def walk(cs):
            for c in cs or []:
                if c.get("type") in (None, "library", "framework", "application", "container", "operating-system", "file"):
                    sup = (c.get("supplier") or {}).get("name") or c.get("publisher") or c.get("author") or ""
                    rows.append({"name": (f"{c['group']}/" if c.get("group") else "") + str(c.get("name", "")), "version": str(c.get("version") or ""),
                                 "purl": str(c.get("purl") or ""), "license": _cdx_lic(c), "supplier": str(sup), "type": c.get("type") or ""})
                walk(c.get("components"))
        walk(d.get("components"))
        return "CycloneDX " + str(d.get("specVersion", "")), rows
    if "spdxVersion" in d or "packages" in d:
        for p in d.get("packages") or []:
            purl = next((r.get("referenceLocator") for r in p.get("externalRefs") or [] if r.get("referenceType") == "purl"), "")
            lic = p.get("licenseConcluded") or ""
            if str(lic).upper() in ("", "NOASSERTION"):
                lic = p.get("licenseDeclared") or ""
            sup = str(p.get("supplier") or "")
            rows.append({"name": str(p.get("name", "")), "version": str(p.get("versionInfo") or ""), "purl": str(purl or ""),
                         "license": "" if str(lic).upper() == "NOASSERTION" else str(lic), "supplier": "" if sup.upper() == "NOASSERTION" else re.sub(r"^(Organization|Person):\s*", "", sup),
                         "type": ""})
        return str(d.get("spdxVersion", "SPDX")), rows
    raise SbomError("This JSON is not a CycloneDX or SPDX SBOM.")


def _match(lic: str, lst: list[str]) -> bool:
    ids = [p.strip("() ").lower() for p in re.split(r"\s+(?:OR|AND|WITH)\s+", lic, flags=re.I) if p.strip("() ")]
    for pat in lst:
        rx = re.compile("^" + re.escape(pat.lower()).replace(r"\*", ".*") + "$")
        if any(rx.match(i) for i in ids):
            return True
    return False


def analyse(text: str, deny: str = "", allow: str = "") -> dict[str, Any]:
    t = str(text or "").strip()
    if not t:
        raise SbomError("Paste an SBOM: CycloneDX JSON or SPDX JSON (syft -o cyclonedx-json, cdxgen, trivy --format cyclonedx).")
    try:
        d = json.loads(t)
    except ValueError as e:
        raise SbomError(f"The JSON could not be read: {e}")
    if not isinstance(d, dict):
        raise SbomError("This JSON is not a CycloneDX or SPDX SBOM.")
    fmt, rows = _parse(d)
    rows = [r for r in rows if r["name"]]
    if not rows:
        raise SbomError("The SBOM lists no components.")
    dn = [x.strip() for x in str(deny or "").split(",") if x.strip()]
    al = [x.strip() for x in str(allow or "").split(",") if x.strip()]
    issues, add = finder()
    eco: dict[str, int] = {}
    for r in rows:
        m = re.match(r"pkg:([\w.-]+)/", r["purl"])
        r["eco"] = m.group(1) if m else "(no purl)"
        eco[r["eco"]] = eco.get(r["eco"], 0) + 1
        r["family"] = family(r["license"])
        fl = []
        alts = [x.strip("() ") for x in re.split(r"\s+OR\s+", r["license"], flags=re.I)] if r["license"] else []
        if dn and alts and all(_match(x, dn) for x in alts):
            fl.append("denied licence")
        elif al and alts and not any(_match(x, al) for x in alts):
            fl.append("not on the allow list")
        if r["family"] == "unknown":
            fl.append("no licence")
        if not r["version"]:
            fl.append("no version")
        if not r["purl"]:
            fl.append("no purl")
        r["flags"] = fl
    fams = {f: sum(1 for r in rows if r["family"] == f) for f in ("permissive", "weak", "strong", "unknown")}
    lic: dict[str, int] = {}
    for r in rows:
        lic[r["license"] or "(none)"] = lic.get(r["license"] or "(none)", 0) + 1
    vers: dict[str, set] = {}
    for r in rows:
        vers.setdefault(f"{r['eco']}:{r['name']}", set()).add(r["version"])
    multi = sorted(((k.split(":", 1)[1], sorted(v)) for k, v in vers.items() if len(v) > 1), key=lambda x: -len(x[1]))
    den = [r for r in rows if "denied licence" in r["flags"]]
    if den:
        add("bad", "Denied licence", f"{len(den)} component(s) carry a licence on your deny list, e.g. {den[0]['name']} ({den[0]['license']}).",
            "Replace them, or get the licence reviewed for how you ship.", den[0]["name"])
    notal = [r for r in rows if "not on the allow list" in r["flags"]]
    if notal:
        add("warn", "Not allowed yet", f"{len(notal)} component(s) use licences not on your allow list, e.g. {notal[0]['name']} ({notal[0]['license']}).", "Review and add them, or replace.", notal[0]["name"])
    strong = [r for r in rows if r["family"] == "strong" and "denied licence" not in r["flags"]]
    if strong:
        add("warn", "Strong copyleft", f"{len(strong)} component(s) are strong copyleft (GPL / AGPL family), e.g. {strong[0]['name']} ({strong[0]['license']}) - check this against how you ship.",
            "Have the licence reviewed; AGPL also reaches software offered over a network.", strong[0]["name"])
    if fams["unknown"]:
        unk = [r for r in rows if r["family"] == "unknown"]
        add("warn", "No licence", f"{fams['unknown']} component(s) have no licence the SBOM can name, e.g. {unk[0]['name']}.", "Find the licence at the source; no licence means no permission.", unk[0]["name"])
    nov = sum(1 for r in rows if "no version" in r["flags"])
    if nov:
        add("info", "No version", f"{nov} component(s) have no version - a vulnerability scan cannot match them.", "Generate the SBOM from the lock file or the built image.")
    nop = sum(1 for r in rows if "no purl" in r["flags"])
    if nop:
        add("info", "No package URL", f"{nop} component(s) have no purl.", "Use a generator that writes purls (syft, cdxgen).")
    if multi:
        add("info", "Several versions", f"{len(multi)} package(s) appear at more than one version, e.g. {multi[0][0]} ({', '.join(multi[0][1][:4])}).", "Deduplicate where you can - each copy is patched separately.")
    nosup = sum(1 for r in rows if not r["supplier"])
    rows.sort(key=lambda r: (0 if "denied licence" in r["flags"] else 1 if r["family"] == "strong" else 2 if r["family"] == "unknown" else 3, r["name"]))
    res = {"format": fmt, "components": len(rows), "families": fams, "ecosystems": dict(sorted(eco.items(), key=lambda kv: -kv[1])),
           "licenses": sorted(lic.items(), key=lambda kv: -kv[1])[:30], "multi": multi[:40], "no_supplier": nosup, "rows": rows[:1500], "deny": dn, "allow": al,
           "verdict": f"{len(rows)} component(s): {fams['permissive']} permissive, {fams['weak']} weak copyleft, {fams['strong']} strong copyleft, {fams['unknown']} unknown"}
    res["note"] = "Licences are read as the SBOM states them; the families are a guide, not legal advice. Nothing is looked up online."
    return finish(res, issues)
