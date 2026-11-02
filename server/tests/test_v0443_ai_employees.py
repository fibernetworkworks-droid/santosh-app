"""v0.443 AI EMPLOYEES PEHLE: the console sidebar's "Employees" section is now "AI Employees" and it sits FIRST
(owner: "MAKE A SECTION IN SIDE BAR INSTEAD OF EMPLOYEE A AI EMPLOYEE FIRST")."""
from __future__ import annotations

from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
V2 = (CON / "v2.js").read_text()
EMP = (CON / "employees.js").read_text()
HTML = (CON / "v2.html").read_text()


def test_the_section_is_named_ai_employees_and_goes_first():
    assert "NAV.unshift(['hire', 'AI Employees'])" in V2 and "NAV.push(['hire'" not in V2
    assert "hire:'· AI Employees'" in V2
    assert 'id="v-hire" aria-label="AI Employees"' in HTML


def test_the_page_and_its_links_say_ai_employees():
    assert V2.count("'Employees'") == 0
    assert EMP.count("<h2>AI Employees</h2>") == 3 and "<h2>Employees</h2>" not in EMP
    assert ">Go to AI Employees<" in EMP and ">Go to Employees<" not in EMP
    assert " in Employees first." not in EMP and " in Employees to " not in EMP


def test_the_icon_is_a_person_with_a_spark():
    line = next(l for l in V2.splitlines() if l.startswith("IC.hire ="))
    assert "M18 2.5l1.1 2.4" in line          # the spark = AI
    assert "M22 11h-6" not in line            # the old plain person + sign is gone
