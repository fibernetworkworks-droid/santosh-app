"""v0.246.0 the console workspace: drag edge instead of the width bar; documents fill the workspace."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.292.0"
    assert "0.292.0+332" in (ROOT / "pubspec.yaml").read_text()


def test_no_width_bar_and_a_drag_edge():
    js = (CON / "workspace.js").read_text()
    assert "Workspace width <input" not in js and 'type="range"' not in js
    for k in ("h.className='workspace-handle'", "setAttribute('role','separator')", "pointerdown", "dblclick",
              "hoola.web.workspace.width", "ArrowLeft", "workspace-full", "workspace-resizing"):
        assert k in js, k


def test_documents_fill_without_the_page_strip():
    js = (CON / "panel.js").read_text()
    assert "navpanes=0" in js and "pagemode=none" in js and "view=FitH" in js
    assert js.count("docView(t, view,") == 3                 # the helper + PDFs + Office-as-PDF (v0.248 draws them itself)
    css = (CON / "v2.css").read_text()
    assert css.count("{") == css.count("}")
    tail = css[css.index("v0.244 WORKSPACE EDGE"):]
    for rule in ("#app .pnview.doc{", "#app .pnview.doc .pnframe{flex:1", "#app .workspace-handle{position:absolute",
                 "#app.workspace-resizing iframe", "#app.workspace-full.st .studio,#app.workspace-full.pn .panel{"):
        assert rule in tail, rule
