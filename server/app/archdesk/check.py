"""v0.417 Architecture Desk live check: `python -m app.archdesk check` / vps-ops `archdesk_check`.

Proves the Principal Software Architect works on THIS server, in three steps:
  1. draw   - two fixed Mermaid diagrams in the server's own Chromium (free, no model)
  2. sums   - the capacity sheet from fixed numbers (free, no model)
  3. design - ONE real Opus design for a fixed sample brief, run the same way her designs run
              (diagrams, one fix round, Markdown, PDF), skipped with --free.
It works as its own check tenant (`__archcheck__`), never hers: her designs, her daily limit and her hire are untouched,
and everything it made (hire row, design row, files) is removed at the end. Exit code 0 = every step OK.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

TENANT = "__archcheck__"
BRIEF = ("Online grocery ordering for a kirana chain in Pune: customers order on the phone app, shop staff pack, "
         "riders deliver within 30 minutes. About 50,000 people a day, the evening 6-9 pm rush is the peak. "
         "UPI payments, Hindi + English, a small monthly budget.")
KIND_BRIEFS = {                      # assess / migrate need her own repo, so the check runs the four that do not
    "design": BRIEF,
    "decide": BRIEF + " Decide for its orders, stock and payments data: PostgreSQL, MongoDB or Firebase Firestore?",
    "threat": BRIEF + " Make the threat model (STRIDE) of the whole system: phone apps, API, payments, riders.",
    "scale": BRIEF + " Plan for 10x and 100x the users: what breaks first and what to change before it does.",
}
DIAGRAMS = [
    {"name": "Check flowchart", "mermaid": "flowchart LR\n  A[Customer app] --> B[API]\n  B --> C[(Orders DB)]\n  B --> D[Rider app]"},
    {"name": "Check sequence", "mermaid": "sequenceDiagram\n  participant C as Customer\n  participant S as Server\n"
                                          "  C->>S: place order\n  S-->>C: order id"},
]


def _step_draw() -> dict[str, Any]:
    from . import diagrams
    out: dict[str, Any] = {"mermaid_file": diagrams.MERMAID.is_file(), "available": diagrams.available()}
    if not out["available"]:
        out["ok"] = False
        out["error"] = "Playwright / vendored Mermaid missing on this server"
        return out
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="hoola-archcheck-") as tmp:
        res = diagrams.render(DIAGRAMS, Path(tmp))
        out["diagrams"] = [{"name": r["name"], "ok": r["ok"], "error": r["error"][:200],
                            "svg_bytes": (Path(tmp) / r["svg"]).stat().st_size if r["svg"] else 0,
                            "png_bytes": (Path(tmp) / r["png"]).stat().st_size if r["png"] else 0} for r in res]
    out["seconds"] = round(time.time() - t0, 1)
    out["ok"] = all(d["ok"] and d["svg_bytes"] > 200 and d["png_bytes"] > 200 for d in out["diagrams"])
    return out


def _step_sums() -> dict[str, Any]:
    from . import capacity
    cap = capacity.compute({"dau": 50000, "peak_factor": 3}, {"dau": "her", "peak_factor": "her"})
    rows = {r["what"]: r["value"] for r in cap["rows"]}
    src = {i["key"]: i["source"] for i in cap["inputs"]}
    return {"ok": bool(rows) and src.get("dau") == "her" and src.get("requests_per_user_per_day") == "assumed",
            "rows": rows, "assumed": cap.get("assumed")}


def _master(x: dict[str, Any]) -> dict[str, Any]:
    """The MASTER parts of a finished job, in a few lines a person can read."""
    chk = x.get("checks") or []
    rv = x.get("review") or {}
    out: dict[str, Any] = {"kind": x.get("kind"),
                           "peer_review": f"{len(rv.get('issues') or [])} issue(s), "
                                          + ("revised" if rv.get("revised") else rv.get("verdict", "not run")),
                           "checks": f"{sum(1 for c in chk if c['ok'])}/{len(chk)} pass",
                           "checks_failed": [c["check"] + (f" ({c['detail']})" if c.get("detail") else "") for c in chk if not c["ok"]],
                           "api": ("valid, %s operations" % (x.get("api_check") or {}).get("operations")) if (x.get("api_check") or {}).get("ok")
                           else ((x.get("api_check") or {}).get("error") or "none"),
                           "boundary_rules": len(x.get("fitness_rules") or []),
                           "breaks_first": [f"{b['at']}: {b['what']}" for b in (x.get("scenarios") or {}).get("breaks") or []]}
    dr = x.get("decision_result") or {}
    if dr:
        out["decision"] = dr.get("error") or {"winner": dr.get("winner"), "margin": dr.get("margin"), "robust": dr.get("robust"),
                                              "totals": {t["option"]: t["score"] for t in dr.get("totals") or []},
                                              "missing_scores": dr.get("missing")}
    tr = x.get("threat_result") or {}
    if tr:
        out["threats"] = {"total": tr.get("total"), "open_high": tr.get("open_high"), "not_considered": tr.get("letters_unused"),
                          "parts_without_threats": len(tr.get("uncovered") or [])}
    if x.get("scale_plan"):
        out["scale_plan"] = [f"{s['at']}: {s['breaks']}" for s in x["scale_plan"]][:6]
    return out


def _step_design(kind: str = "design") -> dict[str, Any]:
    from ..employee import hire
    from . import service as A
    A.ensure_table()
    hire.hire(TENANT, A.HIRE_KEY)
    pid = ""
    spawn = A._spawn
    A._spawn = lambda fn, *a: None          # run the job inline below instead of in a thread
    t0 = time.time()
    try:
        pid = A.start(TENANT, "", KIND_BRIEFS.get(kind, BRIEF), "", None, kind)["id"]
        A.run(pid)
        v = A.get(TENANT, pid)
        vdir = A._pdir(TENANT, pid) / f"v{v.get('version') or 1}"
        d = v.get("design") or {}
        cap = v.get("capacity") or {}
        drawn = v.get("diagrams") or []
        out = {"seconds": round(time.time() - t0, 1), "status": v.get("status"), "stage": v.get("stage"),
               "error": v.get("error") or "", "title": v.get("title"),
               "adrs": len(d.get("adrs") or []), "risks": len(d.get("risks") or []),
               "components": len(d.get("components") or []),
               "diagrams": f"{sum(1 for g in drawn if g.get('ok'))}/{len(drawn)} drawn",
               "diagram_errors": [f"{g.get('name')}: {str(g.get('error'))[:120]}" for g in drawn if not g.get("ok")],
               "capacity_rows": len(cap.get("rows") or []), "capacity_error": cap.get("error", ""),
               "dau_source": next((i.get("source") for i in cap.get("inputs") or [] if i.get("key") == "dau"), None),
               "pdf_bytes": (vdir / "design.pdf").stat().st_size if (vdir / "design.pdf").is_file() else 0,
               "md_bytes": (vdir / "design.md").stat().st_size if (vdir / "design.md").is_file() else 0,
               "master": _master(v.get("extra") or {})}
        x = v.get("extra") or {}
        out["ok"] = (out["status"] == "waiting_her" and out["adrs"] > 0 and out["capacity_rows"] > 0
                     and out["pdf_bytes"] > 1000 and bool(drawn) and any(g.get("ok") for g in drawn)
                     and bool(x.get("checks")) and bool(x.get("review"))
                     and (kind != "decide" or bool((x.get("decision_result") or {}).get("totals")))
                     and (kind != "threat" or bool((x.get("threat_result") or {}).get("rows"))))
        return out
    except Exception as e:      # noqa: BLE001 - the check reports, never crashes
        return {"ok": False, "seconds": round(time.time() - t0, 1), "error": f"{type(e).__name__}: {e}"[:500]}
    finally:
        A._spawn = spawn
        if pid:
            try:
                A.delete(TENANT, pid)
            except Exception:   # noqa: BLE001
                pass
        try:
            hire.leave(TENANT, A.HIRE_KEY)
        except Exception:       # noqa: BLE001
            pass


def _paths(routes) -> list[str]:
    """Every route path, also inside included routers (newer FastAPI keeps them nested, not flattened)."""
    out: list[str] = []
    for r in routes:
        if getattr(r, "path", None) and not hasattr(r, "original_router"):
            out.append(str(r.path))
        inner = getattr(getattr(r, "original_router", None), "routes", None)
        if inner:
            out += _paths(inner)
    return out


def live_check(free: bool = False, kinds: tuple[str, ...] = ("design",)) -> dict[str, Any]:
    from .. import main as _main  # noqa: F401 - the same app wiring the live server uses (routes, models)
    res: dict[str, Any] = {"version": getattr(_main, "APP_VERSION", "?")}
    res["routes"] = sorted({p for p in _paths(_main.app.router.routes) if p.startswith("/api/arch/")})
    res["draw"] = _step_draw()
    res["sums"] = _step_sums()
    jobs = {} if free else {k: _step_design(k) for k in kinds}
    res["design"] = {"ok": True, "skipped": "--free"} if free else {"ok": all(j["ok"] for j in jobs.values()), "jobs": jobs}
    res["ok"] = bool(res["routes"]) and all(res[k]["ok"] for k in ("draw", "sums", "design"))
    return res


def main(argv: list[str]) -> int:
    from ..db import init_db
    init_db()
    kinds: tuple[str, ...] = ("design",)
    for a in argv:
        if a.startswith("--kind"):
            v = a.split("=", 1)[1] if "=" in a else (argv[argv.index(a) + 1] if argv.index(a) + 1 < len(argv) else "design")
            kinds = tuple(KIND_BRIEFS) if v == "all" else tuple(k for k in v.split(",") if k in KIND_BRIEFS) or ("design",)
    res = live_check(free="--free" in argv, kinds=kinds)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print("\nARCHDESK CHECK:", "OK" if res["ok"] else "PROBLEM",
          "- draw", "ok" if res["draw"]["ok"] else "FAIL",
          "| sums", "ok" if res["sums"]["ok"] else "FAIL",
          "| design", "skipped" if res["design"].get("skipped") else
          " ".join(f"{k} {'ok' if j['ok'] else 'FAIL'}" for k, j in res["design"].get("jobs", {}).items()))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
