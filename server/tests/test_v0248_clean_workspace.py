"""v0.248.0 the console workspace: our own PDF reader (no browser toolbar / grey canvas) and one header row for one item."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.318.0"
    assert "0.318.0+358" in (ROOT / "pubspec.yaml").read_text()


def test_pdfjs_vendored_and_loaded_lazily():
    v = CON / "vendor" / "pdfjs"
    for f in ("pdf.min.js", "pdf.worker.min.js", "LICENSE"):
        assert (v / f).exists(), f
    assert "Apache License" in (v / "LICENSE").read_text()
    js = (CON / "pdfview.js").read_text()
    assert "window.HoolaPdf" in js and "isEvalSupported: false" in js          # the console CSP has no unsafe-eval
    assert "workerSrc" in js and "IntersectionObserver" in js and "renderTextLayer" in js
    html = (CON / "v2.html").read_text()
    assert html.index("pdfview.js") < html.index("panel.js")
    assert "pdf.min.js" not in html                                           # PDF.js itself only when a PDF opens


def test_panel_uses_the_reader_and_one_header_row():
    js = (CON / "panel.js").read_text()
    assert "window.HoolaPdf.mount(view, bytes.slice(0), name)" in js
    assert "#toolbar=0&navpanes=0" in js                                     # the fallback hides the browser toolbar too
    assert "t.pdf?.destroy()" in js
    assert '<div class="pnslot"></div>' in js and "function syncHead()" in js and "box.classList.toggle('one', !!one)" in js
    css = (CON / "v2.css").read_text()
    assert css.count("{") == css.count("}")
    tail = css[css.index("v0.248 CLEAN WORKSPACE"):]
    for rule in ("#app .panel.one .pntabs{display:none}", ".pdfpage{", ".pdfpill{", ".pdfpage .textLayer{"):
        assert rule in tail, rule


def test_pdfjs_is_served(env):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    for f in ("pdfview.js", "vendor/pdfjs/pdf.min.js", "vendor/pdfjs/pdf.worker.min.js"):
        assert c.get("/static/console/" + f).status_code == 200, f
