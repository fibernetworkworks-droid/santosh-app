"""v0.910 AI EMPLOYEES PRO: the phone's AI Employees hub shows the console's departments from the real catalog."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "lib/ui/shell/hoola_employees.dart"


def test_every_catalog_department_has_its_own_card():
    from app.employee import hire
    groups = {c.get("group") or "Business" for c in hire.CATALOG.values()}
    dart = PAGE.read_text()
    known = set(re.findall(r"\(group: '([^']+)'", dart))
    assert groups <= known, groups - known   # a new group still shows (hoolaDeptOf) but should get its own drawing
    icons = re.findall(r"icon: '([^']+)'\)", dart)
    assert len(icons) == len(set(icons)) == len(known) + 1, "every department its own drawing (+ the plain one for a new group)"


def test_same_routes_and_trust_levels_as_the_console():
    api = (ROOT / "lib/api.dart").read_text()
    assert "'/api/employees'" in api and "/api/employees/$key/$action" in api and "/api/employees/$key/settings" in api
    main = (ROOT / "server/app/main.py").read_text()
    assert '@app.put("/api/employees/{key}/settings"' in main and '"trust"' in main
    from app.employee import hire
    dart = PAGE.read_text()
    for t in hire.TRUST:
        assert f"'{t}': (" in dart, t
    console = (ROOT / "server/app/static/console/employees.js").read_text()
    # the department lines are the console's own words
    assert "Marketing, customers and back office for your shop or company." in console
    assert "Marketing, customers and back office for your shop or company." in dart


def test_the_three_levels_and_tests_wired():
    dart = PAGE.read_text()
    for name in ("class HoolaDepartmentPage", "class HoolaEmployeePage", "class HoolaStaff", "class DeptBadge"):
        assert name in dart, name
    assert "employees_pro_test.dart" in (ROOT / ".github/workflows/app-screens.yml").read_text()
    shots = (ROOT / "test/goldens/screens_test.dart").read_text()
    assert "63_employees_dept_" in shots and "64_employees_one_" in shots


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.914.0"
    assert "version: 0.914.0+913" in (ROOT / "pubspec.yaml").read_text()
