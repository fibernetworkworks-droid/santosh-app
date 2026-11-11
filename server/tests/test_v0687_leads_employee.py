"""v0.691.0 LEADS EMPLOYEE: the Lead Generation employee joins the AI Employees hub's Business department
(owner: "PERFECT NOW CHECK IN AI EMPLOYE :: BUSINESS SECTION IN WEB CONSOLVE ---- AND PUT THE LEAD GENEARTION
AI EMPLOYEE IN THAT SECTION") + its Leads Desk in the web console.

The engine itself is v0.684.0's P0-P5 (test_v0540..test_v0545); this release gives it the catalog row, the desk
surface over the REAL /api/leads/* routes, and the EDU_OPEN law: the six leads tools were open to every user
before this row existed, so hiring only adds the desk - no leads tool starts checking is_hired().
Zero network: every check is the catalog, the DB, or the console sources."""
from __future__ import annotations

from pathlib import Path

import pytest

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
EMP = (CON / "employees.js").read_text(encoding="utf-8")
V2 = (CON / "v2.js").read_text(encoding="utf-8")
HTML = (CON / "v2.html").read_text(encoding="utf-8")
SRV = Path(__file__).resolve().parents[1]

T = "default"


# ---------------------------------------------------------------- the catalog row
def test_leads_row_in_the_business_department(env):
    from app.employee import hire
    cat = {c["key"]: c for c in hire.catalog(T)}
    e = cat["leads"]
    assert e["name"] == "Lead Generation" and e["group"] == "Business" and e["live"] is True
    assert "never contacts anyone" in e["pitch"] and "two taps" in e["pitch"]
    assert len(e["does"]) >= 6 and len(e["needs"]) == 4 and len(e["never"]) >= 6
    joined = " ".join(e["does"])
    assert "IndiaMART" in joined and "Places" in joined and "CONFIRM CARD" in joined and "ledger" in joined
    needs = " ".join(e["needs"])
    assert "opt-in" in needs and "OFF until you switch it on" in needs and "priced before it runs" in needs
    never = " ".join(e["never"])
    assert "opted out" in never and "Scrape anything until the scrape opt-in is ON" in never
    assert "Hide a send" in never and "Keep what you asked it to forget" in never
    # the honest-cap line: the caps named as the engine enforces them
    assert "5,001-row ask is refused at plan time" in joined and "5,000 rows per run" in joined


def test_the_rest_of_the_catalog_is_untouched(env):
    from app.employee import hire
    cat = {c["key"]: c for c in hire.catalog(T)}
    assert cat["seo"]["live"] and cat["social"]["live"] and cat["paisa_sahayak"]["live"]
    assert cat["accounts"]["live"] and not cat["telecaller"]["live"]   # the "coming" rows still coming (v0.807 accounts went live)
    assert cat["seo"]["group"] == "Business" and hire.catalog(T)[0]["key"]


# ---------------------------------------------------------------- the hire flow (the real DB)
def test_hire_pause_resume_leave_flow(env):
    from app.employee import hire
    with pytest.raises(hire.HireError):
        hire.hire(T, "no-such-key")
    r = hire.hire(T, "leads")
    assert r["key"] == "leads" and r["status"] == "hired" and not r.get("already")
    assert hire.hire(T, "leads")["already"]            # hiring twice is one row
    assert hire.hired_keys(T) == {"leads": "hired"}
    assert {c["key"]: c for c in hire.catalog(T)}["leads"]["status"] == "hired"   # the hub sees it hired
    assert hire.pause(T, "leads")["status"] == "paused" and hire.hired_keys(T) == {"leads": "paused"}
    assert hire.resume(T, "leads")["status"] == "hired"
    assert hire.leave(T, "leads")["status"] == "left" and hire.hired_keys(T) == {}
    assert hire.hire(T, "leads")["status"] == "hired"   # can be hired again (a new row, history kept)


# ---------------------------------------------------------------- the desk wiring (the console sources)
def test_the_desk_exists_and_is_wired():
    assert 'id="v-leadsdesk" aria-label="Leads Desk"' in HTML
    assert "if (v === 'leadsdesk') EMP?.leads($('#leadsdesk'));" in V2
    assert "leadsdesk:'· Leads Desk'" in V2
    assert "['leads', 'leadsdesk', 'Leads Desk']" in V2            # a let-go desk falls back to the hub
    assert "leads: 'leadsdesk'" in EMP                             # Open desk -> Leads Desk
    assert "async function leads(el)" in EMP
    assert "return {hub, desk, social, cad, game, arch, edu, leads};" in EMP
    assert "<h2>Leads Desk</h2>" in EMP and "<h2>Leads Desk</h2>" not in V2
    assert EMP.count("<h2>AI Employees</h2>") == 2                 # the hub's own headings untouched


def test_the_desk_speaks_the_real_surface_and_the_two_tap_law():
    for route in ("/api/leads", "/api/leads/runs?limit=12", "/api/leads/outreach?limit=100",
                  "/api/leads/rows?q=", "/api/leads/campaign-list", "/api/leads/opt-out", "/api/leads/forget"):
        assert route in EMP, route
    api_src = (SRV / "app" / "leads" / "api.py").read_text(encoding="utf-8")
    for route in ('""', '"/runs"', '"/rows"', '"/outreach"', '"/campaign-list"', '"/opt-out"', '"/forget"'):
        assert route in api_src, route                              # every desk call has a real route
    assert "confirm_required" in EMP and "confirm: true" in EMP     # tap one -> card, tap two -> build
    assert "Confirm - build the list" in EMP and "nothing is built until the second tap" in EMP
    assert "Opt out" in EMP and "forget EVERYTHING" in EMP          # the DPO acts on the desk
    assert "data-lopt=\"${esc(w.id)}\"" in EMP                      # every server value through esc()


def test_the_no_desk_rows_contract_still_holds():
    assert "if (/desk$/.test(NAV[i][0])) NAV.splice(i, 1)" in V2    # v0.456: never a desk row in the sidebar
    assert "NAV.push(['leadsdesk'" not in V2 and "NAV.unshift(['leadsdesk'" not in V2


# ---------------------------------------------------------------- the EDU_OPEN law for leads
def test_no_leads_tool_checks_is_hired():
    for rel in ("app/agent/leads_tools.py", "app/leads/service.py", "app/leads/api.py",
                "app/leads/rules.py", "app/leads/importer.py"):
        src = (SRV / rel).read_text(encoding="utf-8")
        assert "is_hired" not in src, rel                           # hiring only adds the desk, never a gate
        assert "working_tenants" not in src, rel


# ---------------------------------------------------------------- the version
def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.821.0"
    pub = Path(__file__).resolve().parents[2] / "pubspec.yaml"
    assert "0.821.0+820" in pub.read_text()
