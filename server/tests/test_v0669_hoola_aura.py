"""v0.669 HOOLA AURA: a soft, slowly drifting Hoola-gradient glow behind the Web Studio home.

Peach / saffron / magenta / violet, heavily blurred, each on its own 26-38 s loop; fades out before the cards so text
stays readable; dimmer in dark; still under reduced motion; never takes a click; home only.
"""
from __future__ import annotations

import re
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

D = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def test_aura_markers():
    js, css = (D / "webstudio.js").read_text(), (D / "webstudio.css").read_text()
    assert '<div class="aura" aria-hidden="true"><i class="a1"></i><i class="a2"></i><i class="a3"></i><i class="a4"></i></div>' in js
    blk = css[css.index("HOOLA AURA"):]
    for c in ("#FFD9A8", "#FF9A3C", "#C055F5", "#8B6CFF"):        # the house gradient + violet
        assert c in blk
    assert "pointer-events:none" in blk and "z-index:-1" in blk and "mask-image" in blk
    secs = [int(s) for s in re.findall(r"animation:aura\d (\d+)s", blk)]
    assert len(secs) == 4 and min(secs) >= 20                      # slow, never busy
    assert "prefers-reduced-motion" in blk and "animation:none" in blk
    assert "data-theme" in blk or "prefers-color-scheme:dark" in blk


def test_aura_in_browser(arena_server):
    base, browser, key = arena_server
    errors = []
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        p = ctx.new_page()
        p.on("pageerror", lambda e: errors.append(str(e)))
        p.goto(base + "/console/web#/")
        p.wait_for_selector("#wsAsk", timeout=20000)
        info = p.evaluate("""() => { const a = document.querySelector('.aura'); const i = a.querySelector('i');
            const r = a.getBoundingClientRect(); const s = getComputedStyle(i);
            return {n: a.querySelectorAll('i').length, pe: getComputedStyle(a).pointerEvents, w: r.width,
                    anim: s.animationName, op: +s.opacity, blur: s.filter}; }""")
        assert info["n"] == 4 and info["pe"] == "none" and info["w"] > 600
        assert info["anim"].startswith("aura") and "blur" in info["blur"]
        if scheme == "dark":
            assert info["op"] <= 0.25
        top = p.evaluate("() => { const b = document.querySelector('#wsAsk').getBoundingClientRect();"
                         " return document.elementFromPoint(b.x + 20, b.y + 10).closest('.aura') === null; }")
        assert top                                                   # the ask box stays clickable
        ctx.close()
    assert not errors, errors
