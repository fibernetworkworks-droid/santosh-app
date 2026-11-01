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


def _step_design() -> dict[str, Any]:
    from ..employee import hire
    from . import service as A
    A.ensure_table()
    hire.hire(TENANT, A.HIRE_KEY)
    pid = ""
    spawn = A._spawn
    A._spawn = lambda fn, *a: None          # run the job inline below instead of in a thread
    t0 = time.time()
    try:
        pid = A.start(TENANT, "", BRIEF)["id"]
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
               "md_bytes": (vdir / "design.md").stat().st_size if (vdir / "design.md").is_file() else 0}
        out["ok"] = (out["status"] == "waiting_her" and out["adrs"] > 0 and out["capacity_rows"] > 0
                     and out["pdf_bytes"] > 1000 and bool(drawn) and any(g.get("ok") for g in drawn))
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


def live_check(free: bool = False) -> dict[str, Any]:
    from .. import main as _main  # noqa: F401 - the same app wiring the live server uses (routes, models)
    res: dict[str, Any] = {"version": getattr(_main, "APP_VERSION", "?")}
    res["routes"] = sorted({p for p in _paths(_main.app.router.routes) if p.startswith("/api/arch/")})
    res["draw"] = _step_draw()
    res["sums"] = _step_sums()
    res["design"] = {"ok": True, "skipped": "--free"} if free else _step_design()
    res["ok"] = bool(res["routes"]) and all(res[k]["ok"] for k in ("draw", "sums", "design"))
    return res


def main(argv: list[str]) -> int:
    from ..db import init_db
    init_db()
    res = live_check(free="--free" in argv)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print("\nARCHDESK CHECK:", "OK" if res["ok"] else "PROBLEM",
          "- draw", "ok" if res["draw"]["ok"] else "FAIL",
          "| sums", "ok" if res["sums"]["ok"] else "FAIL",
          "| design", "skipped" if res["design"].get("skipped") else ("ok" if res["design"]["ok"] else "FAIL"))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
