"""Run diagram-design's own export_png.py UNCHANGED, with the server's browser.

The vendored script calls `playwright.chromium.launch()` with no options, which only finds a browser that matches the
installed Playwright exactly. Hoola's servers name their browser (HOOLA_DIAGRAM_CHROME, set by runners.dd_png), so this
wrapper gives launch() that path and the usual container flags when the script does not pass its own, then calls the
script's own rasterize(). Run as: python -I _dd_export.py <scripts dir> <src.html> <out.png> <scale>."""
from __future__ import annotations

import os
import pathlib
import sys


def main() -> int:
    scripts, src, out, scale = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
    exe = os.environ.get("HOOLA_DIAGRAM_CHROME", "")
    from playwright.sync_api._generated import BrowserType
    real = BrowserType.launch

    def launch(self, *a, **kw):
        if exe and not kw.get("executable_path"):
            kw["executable_path"] = exe
        kw.setdefault("args", ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
        return real(self, *a, **kw)

    BrowserType.launch = launch
    sys.path.insert(0, scripts)
    import export_png  # the vendored script, as it ships
    export_png.rasterize(pathlib.Path(src), pathlib.Path(out), scale)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
