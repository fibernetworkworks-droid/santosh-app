"""v0.366 IPAD PANE (App Sahayak Phase 30): on a wide iPad (horizontal size class regular) each tab shows its list on the
left and the opened record on the right; a record opened from the list replaces the right side (Router.split), Back closes
it, a quiet placeholder before anything is chosen; iPhone keeps one navigation stack per tab."""
from pathlib import Path

KIT = Path(__file__).resolve().parents[1] / "app/appmaker/ios/template/Sources/Kit/Kit.swift"


def test_root_two_panes_on_ipad():
    s = KIT.read_text()
    assert "@Environment(\\.horizontalSizeClass) private var hsc" in s and "if hsc == .regular {" in s
    assert "if split { paths[tab] = [id] } else { paths[tab].append(id) }" in s
    assert "PanePlaceholder().navigationDestination(for: String.self)" in s and "struct PanePlaceholder: View" in s
    assert ".onAppear { router.split = hsc == .regular }" in s and "static var chooseOne" in s
    assert ".onAppear { if let s = start { router.go(s) } }" in s      # the simulator check still opens screens inside the app
