"""v0.314 CI only: a real Hoola server for the emulator test of the generated app (appgen-check.yml, job "smoke").

    python -m app.appmaker.android.ci_e2e prepare   # fresh database + the fixture app's project (app_key FIXTURE_KEY)
    python -m app.appmaker.android.ci_e2e check     # after the run: the order the APP placed is on the server, priced
                                                    # by the server, exactly once, then printed

Run from server/ with DATABASE_URL set; the server itself is plain uvicorn (app.main:app) on 127.0.0.1:8077, which the
emulator reaches as http://10.0.2.2:8077 (allowed in debug builds only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE_KEY = "akf1c7a2e0000000000000001"


def prepare() -> None:
    from ...db import init_db, session
    from ..models import AppProject
    init_db()
    spec = json.loads((HERE / "fixture" / "spec.json").read_text())
    facts = {"name": "Sharma Kirana", "phone": "9876543210", "upi_id": "sharmakirana@okicici",
             "products": [{"name": p["name"], "price": p["price"], "unit": p.get("unit") or ""}
                          for p in spec["seed"]["lists"]["products"]]}
    with session() as s:
        s.add(AppProject(id="app_fixture", tenant_id="default", number="A-0001", name="Sharma Kirana", goal="shop",
                         status="approved", plan="{}", facts=json.dumps(facts), android=json.dumps({"app_key": FIXTURE_KEY})))
    print("prepared app_fixture with", len(facts["products"]), "products")


def check() -> int:
    from ...db import session
    from ...site import webapp as W
    from ..models import AppProject
    spec = json.loads((HERE / "fixture" / "spec.json").read_text())
    first = spec["seed"]["lists"]["products"][0]
    with session() as s:
        rows = s.query(W.SiteAppRow).filter(W.SiteAppRow.site_id == "app:app_fixture", W.SiteAppRow.coll == "orders").all()
        data = [json.loads(r.data) for r in rows]
        r = s.get(AppProject, "app_fixture")
        made = bool(r and r.backend)
    crashes = {}
    try:                                    # v0.324 the crash report the app sent
        from ..backend import _crash_file
        with session() as s:
            r2 = s.get(AppProject, "app_fixture")
            s.expunge(r2)
        cf = _crash_file(r2)
        crashes = json.loads(cf.read_text()) if cf.exists() else {}
    except Exception as e:                  # noqa: BLE001
        print("crash file:", e)
    print(json.dumps(data, ensure_ascii=False, indent=1))
    print("crashes:", json.dumps(list(crashes.values())[:2], indent=1)[:1500])
    two = [d for d in data if d.get("items", "").startswith("2 x ")]
    ok = made and len(two) == 1 and abs(float(two[0].get("total") or 0) - 2 * float(first["price"])) < 0.01 \
        and len([d for d in data if str(d.get("_cid", "")).startswith("e2eDedup")]) == 1 \
        and any(d.get("paid") == "Customer says paid" and d.get("utr") == "412345678901" for d in data) \
        and any("hoola e2e crash" in str(c.get("exception")) and "cart" in (c.get("screens") or []) for c in crashes.values())
    print("SERVER CHECK", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    elif sys.argv[1:] == ["check"]:
        sys.exit(check())
    else:
        print(__doc__)
        sys.exit(2)
