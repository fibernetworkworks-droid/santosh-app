"""The service catalog checked the way a platform team scores its golden path: Backstage `catalog-info.yaml` entities (Component,
API, System, Resource, Group, User, Domain - one file or many documents) each scored against her checks (an owner that exists,
a lifecycle, a system, a description, docs, an on-call, a source repository, a runbook), references that point at nothing,
dependency loops, production services that depend on deprecated ones, and ownerless or orphaned entities."""
from __future__ import annotations

import re
from typing import Any

import yaml

from .common import PfInputError, finder, finish


class CatalogError(PfInputError):
    pass


CHECKS = {
    "owner": "has an owner",
    "owner_known": "its owner is a group or user in the catalog",
    "lifecycle": "has a lifecycle (production / experimental / deprecated)",
    "system": "belongs to a system",
    "description": "has a description",
    "docs": "has docs (techdocs-ref or a docs link)",
    "oncall": "has an on-call (PagerDuty / Opsgenie / on-call link)",
    "repo": "has its source repository (project-slug or source-location)",
    "runbook": "has a runbook link",
    "tags": "has tags",
}
DEFAULT_CHECKS = ("owner", "owner_known", "lifecycle", "system", "description", "docs", "oncall", "repo", "runbook")


def _ref(r: str, kind: str, ns: str) -> str:
    """Backstage entity ref -> kind:namespace/name (lower case)."""
    r = str(r or "").strip().lower()
    k, rest = (r.split(":", 1) if ":" in r else (kind.lower(), r))
    n, name = (rest.split("/", 1) if "/" in rest else (ns, rest))
    return f"{k}:{n}/{name}"


def read(text: str) -> list[dict[str, Any]]:
    t = str(text or "").strip()
    if not t:
        raise CatalogError("Paste catalog-info.yaml - one or many entities separated by ---.")
    chunks = re.split(r"(?m)^##\s+\S.*$", t) if re.search(r"(?m)^##\s+\S", t) else [t]
    ents = []
    for ch in chunks:
        try:
            docs = [d for d in yaml.safe_load_all(ch) if d]
        except yaml.YAMLError as e:
            raise CatalogError(f"The YAML could not be read: {str(e).splitlines()[0][:120]}")
        for d in docs:
            if isinstance(d, dict) and d.get("kind") == "Location":
                continue
            if not isinstance(d, dict) or "kind" not in d or not isinstance(d.get("metadata"), dict):
                raise CatalogError("Each document needs kind and metadata (a Backstage entity).")
            ents.append(d)
    if not ents:
        raise CatalogError("No entities found.")
    return ents


def analyse(text: str, checks: str = "") -> dict[str, Any]:
    ents = read(text)
    want = [c.strip() for c in str(checks or "").split(",") if c.strip()] or list(DEFAULT_CHECKS)
    bad = [c for c in want if c not in CHECKS]
    if bad:
        raise CatalogError(f"Unknown check(s): {', '.join(bad)}. Use: {', '.join(CHECKS)}.")
    issues, add = finder()
    by: dict[str, dict[str, Any]] = {}
    for e in ents:
        md = e["metadata"]
        ns = str(md.get("namespace") or "default").lower()
        key = f"{str(e['kind']).lower()}:{ns}/{str(md.get('name', '')).lower()}"
        if key in by:
            add("warn", "Duplicate", f"{e['kind']} {md.get('name')} is defined twice.", "Keep one definition.")
        by[key] = e
    owners = {k for k in by if k.startswith(("group:", "user:"))}
    deps: dict[str, list[str]] = {}
    broken = []
    rows = []
    for key, e in by.items():
        kind = str(e["kind"])
        if kind not in ("Component", "API", "Resource", "System"):
            continue
        md, sp = e["metadata"], e.get("spec") or {}
        ns = str(md.get("namespace") or "default").lower()
        ann = {str(k).lower(): v for k, v in (md.get("annotations") or {}).items()}
        links = md.get("links") or []
        ltext = " ".join(f"{(l or {}).get('title', '')} {(l or {}).get('url', '')} {(l or {}).get('type', '')}" for l in links if isinstance(l, dict)).lower()
        own = sp.get("owner")
        own_ref = _ref(own, "group", ns) if own else ""
        ok = {
            "owner": bool(own),
            "owner_known": bool(own) and (own_ref in owners or _ref(own, "user", ns) in owners),
            "lifecycle": bool(sp.get("lifecycle")) or kind == "System",
            "system": bool(sp.get("system")) or kind == "System",
            "description": bool(str(md.get("description") or "").strip()),
            "docs": "backstage.io/techdocs-ref" in ann or any(w in ltext for w in ("docs", "documentation", "wiki")),
            "oncall": any(k.startswith(("pagerduty.com/", "opsgenie.com/", "firehydrant.com/", "incident.io/", "grafana/oncall")) for k in ann) or any(w in ltext for w in ("on-call", "oncall", "pager")),
            "repo": any(k in ann for k in ("github.com/project-slug", "gitlab.com/project-slug", "backstage.io/source-location", "dev.azure.com/project-repo", "bitbucket.org/project-slug")),
            "runbook": "runbook" in ltext or any("runbook" in k for k in ann),
            "tags": bool(md.get("tags")),
        }
        applic = [c for c in want if not (kind != "Component" and c in ("oncall", "runbook"))]   # on-call and runbooks belong to running services
        missing = [c for c in applic if not ok[c]]
        score = (len(applic) - len(missing)) / len(applic) if applic else 1.0
        refs = []
        for f, k_ in (("dependsOn", "component"), ("providesApis", "api"), ("consumesApis", "api"), ("dependencyOf", "component")):
            for r in sp.get(f) or []:
                rr = _ref(r, k_, ns)
                refs.append((f, rr))
                if rr not in by:
                    broken.append((md.get("name"), f, r))
                if f == "dependsOn":
                    deps.setdefault(key, []).append(rr)
        if sp.get("system") and _ref(sp["system"], "system", ns) not in by:
            broken.append((md.get("name"), "system", sp["system"]))
        rows.append({"key": key, "kind": kind, "name": md.get("name"), "owner": own or "", "lifecycle": sp.get("lifecycle", ""), "system": sp.get("system", ""),
                     "type": sp.get("type", ""), "score": score, "missing": missing, "deps": [r for f, r in refs if f == "dependsOn"]})
    if not rows:
        raise CatalogError("No Component, API, Resource or System entities found.")
    if broken:
        add("warn", "Broken references", f"{len(broken)} reference(s) point at nothing in the catalog, e.g. {broken[0][0]} -> {broken[0][1]} {broken[0][2]}.",
            "Fix the name, or add the missing entity (it may live in another catalog file you did not paste).")
    noown = [r["name"] for r in rows if "owner" in r["missing"]]
    if noown:
        add("bad", "No owner", f"{len(noown)} entit(ies) have no owner: {', '.join(map(str, noown[:6]))}.", "Every component needs a team that answers for it.")
    unk = [r["name"] for r in rows if r["owner"] and "owner_known" in r["missing"]]
    if unk and owners:
        add("warn", "Unknown owner", f"{len(unk)} entit(ies) name an owner that is not a group or user in the catalog: "
            + ", ".join(f"{r['name']} ({r['owner']})" for r in rows if r['owner'] and 'owner_known' in r['missing'])[:200] + ".", "Add the Group, or correct the owner name.")
    life = {r["key"]: r["lifecycle"] for r in rows}
    for r in rows:
        if life.get(r["key"]) == "production":
            dd = [d for d in r["deps"] if life.get(d) == "deprecated"]
            if dd:
                add("warn", "Deprecated dependency", f"{r['name']} (production) depends on deprecated {', '.join(x.split('/')[-1] for x in dd)}.", "Plan the move off it.", str(r["name"]))
    # loops in dependsOn
    seen, stack, loop = {}, [], None

    def dfs(n: str) -> None:
        nonlocal loop
        if loop:
            return
        seen[n] = 1
        stack.append(n)
        for m in deps.get(n, []):
            if seen.get(m) == 1:
                loop = stack[stack.index(m):] + [m]
                return
            if not seen.get(m):
                dfs(m)
        seen[n] = 2
        stack.pop()
    for n in list(deps):
        if not seen.get(n):
            dfs(n)
    if loop:
        add("warn", "Dependency loop", "Components depend on each other in a loop: " + " -> ".join(x.split("/")[-1] for x in loop) + ".", "Break it - a loop means neither can be released alone.")
    low = [r for r in rows if r["score"] < 0.6]
    if low:
        add("info", "Scorecard", f"{len(low)} of {len(rows)} entit(ies) score under 60%.", "Start with owner, on-call and runbook - they matter most when it breaks.")
    pct_check = {c: sum(1 for r in rows if c not in r["missing"]) / len(rows) for c in want}
    systems: dict[str, list[str]] = {}
    for r in rows:
        if r["kind"] == "Component":
            systems.setdefault(r["system"] or "(no system)", []).append(str(r["name"]))
    avg = sum(r["score"] for r in rows) / len(rows)
    rows.sort(key=lambda r: (r["score"], str(r["name"])))
    res = {"entities": len(by), "scored": len(rows), "rows": rows, "checks": [{"key": c, "say": CHECKS[c], "pass": pct_check[c]} for c in want], "avg": avg,
           "owners": sorted(x.split("/")[-1] for x in owners), "systems": systems, "broken": [list(b) for b in broken[:40]], "loop": loop,
           "verdict": f"{len(rows)} entit(ies) scored, average {avg * 100:.0f}%" + (f"; {len(noown)} without an owner" if noown else "")}
    res["note"] = "Scored from the YAML you pasted; references to entities in other catalog files show as broken until you paste those too."
    return finish(res, issues)
