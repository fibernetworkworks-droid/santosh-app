"""v0.410 Architecture diagrams: Mermaid text -> SVG + PNG, drawn by the vendored Mermaid (11.4.1, MIT,
`archdesk/vendor/mermaid.min.js`) inside the headless Chromium Hoola already has.

The diagram text comes from the model, so it is DATA: Mermaid runs with securityLevel "strict" (no click handlers, no
HTML labels, no links), the page can load nothing but its own file (every other request is aborted), and `clean()`
refuses the few Mermaid features that reach outside the picture before Chromium ever sees them. A diagram that does
not draw comes back with Mermaid's own error, so the desk can ask the model to fix just that one.
"""
from __future__ import annotations

import html
import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.archdesk")

MERMAID = Path(__file__).resolve().parent / "vendor" / "mermaid.min.js"
KINDS = ("flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram", "stateDiagram-v2", "erDiagram",
         "C4Context", "C4Container", "C4Component", "C4Deployment")
MAX_CHARS = 12000
_BAD = re.compile(r"(?i)(\bclick\b|\bhref\b|javascript:|<\s*script|%%\{|\bcallback\b|<\s*iframe|<\s*img|on\w+\s*=)")


class DiagramError(Exception):
    pass


def available() -> bool:
    if not MERMAID.is_file():
        return False
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except Exception:
        return False


def clean(text: str) -> str:
    """The diagram text Chromium may see, or DiagramError with the reason (a model's text is never trusted)."""
    t = (text or "").replace("\r", "").strip()
    t = re.sub(r"^```(?:mermaid)?\s*|\s*```$", "", t).strip()
    if not t:
        raise DiagramError("empty diagram")
    if len(t) > MAX_CHARS:
        raise DiagramError("diagram too big")
    first = t.split()[0]
    if first not in KINDS:
        raise DiagramError(f"unknown diagram kind '{first[:30]}'")
    bad = _BAD.search(t)
    if bad:
        raise DiagramError(f"not allowed in a diagram: {bad.group(0).strip()[:20]}")
    return t


_PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#fff;font-family:Inter,Arial,sans-serif}#out{display:inline-block;padding:16px}</style>
<script src="mermaid.min.js"></script></head><body><div id="out"></div><script>
mermaid.initialize({startOnLoad:false, securityLevel:'strict', theme:'neutral', htmlLabels:false,
  flowchart:{htmlLabels:false, useMaxWidth:false}, sequence:{useMaxWidth:false}, fontFamily:'Inter, Arial, sans-serif'});
window.drawOne = async (txt) => {
  try { const r = await mermaid.render('d' + Math.floor(Math.random() * 1e9), txt);
        document.getElementById('out').innerHTML = r.svg; return {ok: true, svg: r.svg}; }
  catch (e) { document.getElementById('out').innerHTML = ''; return {ok: false, error: String(e && e.message || e).slice(0, 400)}; }
};
</script></body></html>"""


def render(items: list[dict[str, Any]], out_dir: Path) -> list[dict[str, Any]]:
    """[{name, mermaid}] -> [{name, mermaid, ok, error, svg, png}] (svg / png = file names inside out_dir).
    One Chromium for all of them; a diagram that fails keeps its text and the error."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    todo: list[tuple[int, str]] = []
    for i, it in enumerate(items):
        r = {"name": str(it.get("name") or f"Diagram {i + 1}")[:80], "mermaid": str(it.get("mermaid") or ""),
             "ok": False, "error": "", "svg": "", "png": ""}
        try:
            r["mermaid"] = clean(r["mermaid"])
            todo.append((i, r["mermaid"]))
        except DiagramError as e:
            r["error"] = str(e)
        results.append(r)
    if not todo:
        return results
    if not available():
        for i, _ in todo:
            results[i]["error"] = "diagram drawing is not set up on this server (Playwright / Mermaid missing)"
        return results
    from playwright.sync_api import sync_playwright
    from ..docstudio.htmlpdf import _launch_kw
    with tempfile.TemporaryDirectory(prefix="hoola-arch-") as tmp:
        page_file = Path(tmp) / "draw.html"
        page_file.write_text(_PAGE, encoding="utf-8")
        (Path(tmp) / "mermaid.min.js").write_bytes(MERMAID.read_bytes())
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**_launch_kw())
            try:
                ctx = browser.new_context(device_scale_factor=2)
                # nothing leaves the machine: only the local page and the local Mermaid file load
                ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(("file:", "data:")) else r.abort())
                page = ctx.new_page()
                page.goto(page_file.as_uri(), wait_until="load", timeout=60000)
                for i, txt in todo:
                    try:
                        got = page.evaluate("t => window.drawOne(t)", txt)
                    except Exception as e:
                        got = {"ok": False, "error": str(e)[:300]}
                    if not got or not got.get("ok"):
                        results[i]["error"] = (got or {}).get("error") or "did not draw"
                        continue
                    base = f"d{i + 1}"
                    svg = got["svg"]
                    (out_dir / f"{base}.svg").write_text(svg, encoding="utf-8")
                    try:
                        page.locator("#out").screenshot(path=str(out_dir / f"{base}.png"))
                        results[i]["png"] = f"{base}.png"
                    except Exception as e:
                        log.info("diagram png failed: %s", e)
                    results[i].update(ok=True, svg=f"{base}.svg")
            finally:
                browser.close()
    return results


def svg_inline(path: Path) -> str:
    """An SVG file ready to sit inside the PDF's HTML (no XML prolog)."""
    try:
        t = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return re.sub(r"^<\?xml[^>]*>\s*", "", t)


def placeholder(name: str, mermaid: str, error: str) -> str:
    """What the PDF shows for a diagram that did not draw: its name, why, and the text (still useful to an engineer)."""
    return (f"<div class='dfail'><b>{html.escape(name)}</b> could not be drawn ({html.escape(error[:160])}).<pre>"
            f"{html.escape(mermaid[:3000])}</pre></div>")


def dumps(items: list[dict[str, Any]]) -> str:
    return json.dumps(items, ensure_ascii=False)
