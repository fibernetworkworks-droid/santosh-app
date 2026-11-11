"""v0.777 HOOLA DESIGN, phase D3 "systems" (docs/HOOLA_DESIGN_PLAN.md): hd-components.js + design-components.css.

The real test is JavaScript - server/tests/web/design_components_test.js - and runs in a REAL browser (node +
playwright, Chromium) against the real editor with the mock server of design_ui_test.js: create a component with the
keyboard, alt-drag an instance and compare its PIXELS with the component, deep-select a layer inside the instance and
override its text and fill (only that instance changes), edit the main (instances follow, the override stays), reset,
detach, component properties, variants (dropdown + switch), styles (one edit = every user, one undo step), variables
with a mode per frame (the drawn colour is read back), the Assets panel (drag onto the canvas), the library (copy a
component of another file, update it later), deleting a main component, and two editors on one file that must end
with the same document. This file runs it so CI covers it and skips cleanly where node, playwright or Chromium is
missing."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
JS_TEST = HERE / "web" / "design_components_test.js"
DESIGN = HERE.parent / "app" / "static" / "console" / "design"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")


def test_the_file_is_a_plain_strict_script():
    text = (DESIGN / "hd-components.js").read_text(encoding="utf-8")
    assert "'use strict';" in text and text.rstrip().endswith("})();")
    assert "eval(" not in text and "new Function" not in text and "import(" not in text          # strict CSP: script-src 'self'
    assert "innerHTML" not in text and "document.write" not in text and "insertAdjacentHTML" not in text   # document text is data, never HTML
    assert text.isascii(), "keep the source ASCII (\\uXXXX escapes), it must not depend on the served charset"
    # every edit is an op through the store: the only writers are HD.store's own calls
    assert "HD.comp = {" in text
    for name in ("vtree", "createComponent", "createInstance", "detach", "swap", "setOverride", "resetOverride", "combineAsVariants",
                 "setVariant", "createStyle", "applyStyle", "updateStyle", "addVar", "setVarValue", "bind", "setMode", "syncFromLibrary",
                 "updateFromLibrary"):
        assert re.search(rf"\b{name}: ", text[text.index("HD.comp = {"):]), f"HD.comp.{name} is part of the API"
    # a binding key carries "$" so the renderer's own first-mode lookup never overrides the value written into the node
    assert "b['$' + key] = vid" in text
    # the page loads it after hd-ui.js and before hd-app.js, with its stylesheet
    html = (DESIGN / "design.html").read_text(encoding="utf-8")
    assert html.index("hd-ui.js") < html.index("hd-components.js") < html.index("hd-app.js") and "design-components.css" in html
    css = (DESIGN / "design-components.css").read_text(encoding="utf-8")
    assert "text-transform" not in css and not re.search(r"font-weight:\s*(700|800|900|bold)", css)
    assert not re.search(r"font-size:\s*(?:[0-9]|1[01])(?:\.\d+)?px", css), "nothing under 12px"


@needs_node
def test_it_parses():
    run = subprocess.run([NODE, "--check", str(DESIGN / "hd-components.js")], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr[-2000:]


@needs_node
def test_components_instances_variants_styles_variables_in_a_real_browser():
    env = os.environ.copy()
    if env.get("HOOLA_CHROMIUM"):
        env["CHROMIUM_EXECUTABLE"] = env["HOOLA_CHROMIUM"]
    run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=600, env=env)
    if run.returncode != 0 and not env.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists() and "no browser here" in run.stdout:
        env["CHROMIUM_EXECUTABLE"] = SANDBOX_CHROME                  # the same fallback the other browser walks use
        run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=600, env=env)
    if run.returncode == 77:
        pytest.skip((run.stdout.strip().splitlines() or ["no browser here"])[-1])
    assert run.returncode == 0, (run.stdout[-1500:] + "\n" + run.stderr[-4000:])
    assert "design_components_test: ok" in run.stdout
