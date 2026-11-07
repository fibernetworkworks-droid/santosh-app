"""v0.363 BADI SCREEN (App Sahayak Phase 27): Android apps on tablets / unfolded phones / landscape - a bottom bar or pill
becomes a side rail at 600dp+, pages stay a centred readable column (max 720dp), 2-column grids become 3 when there is room;
the CI device check opens every screen again at tablet size; iPhone pages keep a readable width in landscape."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app/appmaker"


def test_android_kit_wide():
    kit = (ROOT / "android/template/app/src/main/java/hoola/kit/Kit.kt").read_text()
    assert "fun isWide(): Boolean" in kit and "screenWidthDp >= 600" in kit
    assert "if (maxWidth > 752.dp) (maxWidth - 720.dp) / 2 else 16.dp" in kit
    assert "if (columns == 2 && maxWidth >= 560.dp) 3 else columns" in kit
    nav = (ROOT / "android/template/app/src/main/java/hoola/kit/Nav.kt").read_text()
    assert 'val railNow = look.nav == "rail" || (wide && barNav)' in nav and "if (railNow && (nav.onTab || split)) Rail(nav)" in nav     # v0.365 also beside an open record
    assert "if (!railNow && look.nav == \"floating_pill\"" in nav


def test_tablet_check_travels_and_runs_in_ci(tmp_path):
    import json
    from app.appmaker.android import gen as G
    sp = json.loads((ROOT / "android/fixture2/spec.json").read_text())
    G.write_project(sp, tmp_path / "p")
    t = (tmp_path / "p/hoola_qa/tablet_check.sh").read_text()
    assert "wm size 1600x2560" in t and "wm size reset" in t and "hoola_screen" in t and '[ "$dead" = 0 ]' in t
    wf = (ROOT.parents[2] / ".github/workflows/appgen-check.yml").read_text()
    assert "hoola_qa/tablet_check.sh" in wf


def test_iphone_page_width():
    assert ".frame(maxWidth: 720, alignment: .leading)" in (ROOT / "ios/template/Sources/Kit/Kit.swift").read_text()
