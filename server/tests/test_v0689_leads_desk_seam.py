"""v0.690.0 LEADS DESK SEAM - the desk said a route the server never served, and the release tests
checked each side SEPARATELY so the broken seam passed both. The owner's screenshot: the Leads Desk
opened to a red "Not Found" - the desk's first load is Promise.all([GET /api/leads/overview,
GET /api/leads/runs, GET /api/leads/outreach]) and the server's overview route is GET /api/leads (the
engine's canonical shape since v0.544: the router itself is the overview). One 404 kills the Promise.all,
the catch paints the message red, the desk looks dead while six of seven routes work.

This release's guard is the SEAM itself:
  1. extract EVERY api('METHOD', '/api/leads...') call from the console sources and check each
     (method, path) against the REAL FastAPI route table - both sides must agree, forever;
  2. the ghost route is gone from the sources;
  3. the desk's exact first-load trio is FIRED over the TestClient with the key auth the console uses:
     all three 200 and the overview carrying the keys the desk renders.

Zero network: the route table and the client are in-process."""
from __future__ import annotations

import re
from pathlib import Path

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)
from tests.test_api import client  # noqa: F401

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"

# every desk call is api('GET'|'POST', '...') - the path stops at ? (query) for both '...' and `...` forms
CALL_RE = re.compile(r"""api\('(GET|POST)',\s*['"`](/api/leads[^'"`?]*)""")

THE_FIRST_LOAD = [("/api/leads", "GET"), ("/api/leads/runs", "GET"), ("/api/leads/outreach", "GET")]


def desk_calls() -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    for f in sorted(CON.glob("*.js")):
        for m in CALL_RE.finditer(f.read_text(encoding="utf-8")):
            calls.append((m.group(2), m.group(1)))
    return calls


def route_table() -> set[tuple[str, str]]:
    from fastapi.routing import APIRoute
    from app.main import app
    return {(r.path, m) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}


# ---------------------------------------------------------------- 1. the seam: desk calls vs real routes
def test_every_desk_call_is_a_route_the_server_serves(env):
    calls = desk_calls()
    assert len(calls) >= 8, calls                      # the desk's full surface is in the sources
    table = route_table()
    for path, method in calls:
        assert (path, method) in table, f"console calls {method} {path} - no such route on the server"
    for path, method in THE_FIRST_LOAD:                # the trio the desk's Promise.all lives on
        assert (path, method) in calls, (path, method)  # and the seam test really saw them


def test_the_ghost_overview_route_is_gone_from_the_sources():
    for f in sorted(CON.glob("*.js")):
        assert "/api/leads/overview" not in f.read_text(encoding="utf-8"), f.name


# ------------------------------------------------- 2. the desk's first load, fired for real (the screenshot)
def test_the_desk_first_load_really_answers(env, monkeypatch):
    from app.leads.models import ensure_tables
    ensure_tables()
    from tests.test_api import client as mk
    with mk(monkeypatch, env, api_key="secret") as c:
        h = {"Authorization": "Bearer secret"}
        o = c.get("/api/leads", headers=h)
        rr = c.get("/api/leads/runs", headers=h, params={"limit": 12})
        out = c.get("/api/leads/outreach", headers=h, params={"limit": 100})
        assert o.status_code == 200 and rr.status_code == 200 and out.status_code == 200, \
            (o.status_code, rr.status_code, out.status_code)
        body = o.json()
        for k in ("store", "usage", "caps", "lanes", "lanes_built", "store_backend", "never",
                  "one_question", "store_boundary"):
            assert k in body, k                        # the keys the desk renders on first paint
        assert isinstance(rr.json().get("runs"), list) and isinstance(out.json().get("events"), list)
        assert out.json().get("kind") == "leads_outreach_log"
        # and the guard law that turned a dead desk into a red "Not Found" stays: no key, 401
        assert c.get("/api/leads").status_code == 401 and c.get("/api/leads/rows").status_code == 401


# ---------------------------------------------------------------- 3. the fix itself, pinned in the source
def test_the_overview_call_is_the_canonical_route():
    emp = (CON / "employees.js").read_text(encoding="utf-8")
    assert "api('GET', '/api/leads')" in emp            # the exact fixed call
    assert "Promise.all([api('GET', '/api/leads')" in emp  # still one first load, all three together
