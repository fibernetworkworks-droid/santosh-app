"""v0.447 AI EMPLOYEES PREMIUM: the console hub is departments -> employees -> details (owner approved the prototype:
"GO. MAKE ALL CARD OF SAME SIZE"). Every card in a grid is the same size; entrances play once per page; hiring keeps
the real API (trust seekh) and Pause / Resume / Let go (with its confirm) stay."""
from __future__ import annotations

from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
EMP = (CON / "employees.js").read_text()
CSS = (CON / "v2.css").read_text()
V2 = (CON / "v2.js").read_text()
BLK = CSS[CSS.index("v0.447 AI EMPLOYEES PREMIUM"):]


def test_departments_then_employees_then_details():
    for k in ("function homePage(", "function deptCard(", "function deptPage(", "function roleCard(", "function panel("):
        assert k in EMP, k
    for g in ("Game Development, Simulation & VR", "Business", "Research, CAD, Hardware & Industrial Tech",
              "Software Architecture, Engineering & Core Systems"):
        assert f"g: '{g}'" in EMP, g
    assert "name: g, art: 'other'" in EMP                       # a group the hub does not know still shows, plainly
    assert 'data-ae="dept"' in EMP and 'data-ae="role"' in EMP and 'data-ae="filter"' in EMP and 'data-ae="home"' in EMP


def test_all_cards_same_size():
    assert ".ae-depts{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));grid-auto-rows:1fr" in BLK
    assert ".ae-roles{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));grid-auto-rows:1fr" in BLK
    assert "ae-feat" not in BLK and "ae-feat" not in EMP          # the prototype's big featured card is gone


def test_hiring_keeps_the_real_actions():
    assert "api('POST', `/api/employees/${encodeURIComponent(key)}/${what}`, what === 'hire' ? {trust: 'seekh'} : undefined)" in EMP
    assert "confirm('Let go of this employee?" in EMP and 'data-ae="${e.status === \'paused\' ? \'resume\' : \'pause\'}"' in EMP
    assert "return {hub, desk, social, cad, game, arch, edu, leads};" in EMP   # v0.453 + the Education Desk


def test_motion_once_and_crisp():
    assert "el.classList.toggle('ae-settled', at === HS.drawn)" in EMP
    assert "#hire.ae-settled .ae-up" in BLK and "#hire.ae-settled .ae-draw{animation:none;stroke-dashoffset:0}" in BLK
    assert "backdrop-filter" not in BLK
    loops = [l for l in BLK.splitlines() if "infinite" in l]
    assert loops == ["#hire .ae-live{background:var(--ok);animation:aePulse 1.8s ease-out infinite}"]   # only the tiny live dot
    assert ":root.calm #hire .ae-draw" in BLK and "@media (prefers-reduced-motion:reduce){#hire .ae-draw" in BLK


def test_every_server_value_is_escaped():
    for k in ("${esc(e.name)}", "${esc(e.pitch || '')}", "${esc(x)}", "${esc(HS.q)}", "${esc(d.name)}"):
        assert k in EMP, k


def test_library_never_lands_inside_the_ai_employees_group():
    assert "NAV.splice(Math.max(0, NAV.findIndex(([k]) => k === 'creative')), 0, ['bana', 'Library'])" in V2
