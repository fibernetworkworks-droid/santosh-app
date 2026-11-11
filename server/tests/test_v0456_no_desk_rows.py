"""v0.456 NO DESK ROWS (owner, with a screenshot of Education Desk / Social Desk / SEO Desk: "REMOVE THIS FORM SIDE BAR").

Hired employees' desks no longer get a sidebar row; each desk opens from AI Employees > Open desk, and the sidebar keeps
only the AI Employees entry (lit while a desk is open)."""
from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
V2 = (CON / "v2.js").read_text(encoding="utf-8")
EMP = (CON / "employees.js").read_text(encoding="utf-8")


def _sync():
    i = V2.index("function syncEmployees(hired) {")
    return V2[i:V2.index("\n}\n", i)]


def test_sync_never_adds_a_desk_row():
    fn = _sync()
    assert "NAV.splice(NAV.findIndex(([k]) => k === 'hire') + 1" not in fn          # the v0.317 insert is gone
    assert "if (/desk$/.test(NAV[i][0])) NAV.splice(i, 1)" in fn                     # and any desk row is dropped
    assert "if (!want && VIEW === view) go('hire');" in fn                            # a let-go desk still falls back
    assert "NAV.push(['" not in fn and "NAV.unshift(" not in fn


def test_desks_still_open_from_the_hub():
    assert "if (openView) openView(v, v === 'systems' || v === 'deptdesk' ? key : '')" in EMP   # v0.796 + the department desks
    for v in ("seodesk", "socialdesk", "caddesk", "gamedesk", "archdesk", "edudesk"):
        assert f"if (v === '{v}') EMP?." in V2, v
    assert "(k === 'hire' && /desk$/.test(VIEW))" in V2                              # AI Employees lit on a desk


def test_no_sidebar_promise_left_in_the_hub():
    assert "in the sidebar" not in EMP


def test_no_lab_or_systems_row():
    """v0.456 'NOW REMOVE LAB AND SYSTEMS': both rows gone; both views still open from their desks."""
    nav = V2[V2.index("const NAV = ["):V2.index("\n", V2.index("const NAV = ["))]
    assert "'lab'" not in nav and "'systems'" not in nav
    assert "NAV.push(['systems'" not in V2 and "NAV.push(['lab'" not in V2
    assert "ENT?.open($('#systems'), arg || 'erp')" in V2                              # Enterprise Open desk -> Systems
    assert "'/static/prayog/lab.html?id=' + encodeURIComponent(arg)" in V2             # Education Desk -> a lab
    assert "openView('lab', b.dataset.edlab)" in EMP
