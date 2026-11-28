"""v0.999.178 LOGIN, PREMIUM (owner, on the design canvas: "A -- GO"): the console login is direction A - Hoola at work
beside you on the left (one real moment, no avatar, no floating bubbles), log in or sign up on the right; ink main
button, Literata for the one warm sentence; Open Gmail for a Gmail address, a 30-second wait before a new code, a
greeting that shows her name. The phone's first screen follows the same design (three steps, six code boxes)."""
from __future__ import annotations

import re
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

APP = Path(__file__).resolve().parents[1] / "app"
ROOT = Path(__file__).resolve().parents[2]


def test_console_markup_is_direction_a():
    h = (APP / "static/console/v2.html").read_text()
    login = h[h.index('<section id="login"'):h.index("</section>", h.index('<section id="login"'))]
    for t in ("The work gets done.", "You stay in charge.", "Ready for your yes", "Continue with Google",
              "Continue with email", "Check your email", "Open Gmail", "What should Hoola call you?",
              "Start using Hoola", "More ways to sign in", "/terms", "/privacy", 'class="lg-go"'):
        assert t in login, t
    assert "santosh-head.png" not in login and "orbit" not in login     # the old avatar + floating bubbles are gone
    css = (APP / "static/console/v2.css").read_text()
    block = css[css.index("v0.999.178 LOGIN, PREMIUM"):]
    assert ".lg-go{" in block and "background:var(--ink)" in block and "@media (max-width:900px)" in block
    assert not re.search(r"#[0-9a-fA-F]{6}", block.split("@media")[0])       # colours only from the theme tokens
    js = (APP / "static/console/v2.js").read_text()
    assert "function lcount()" in js and "#lgmail" in js and "#lgreet" in js


def test_phone_first_screen_follows_the_design():
    d = (ROOT / "lib/ui/setup_screen.dart").read_text()
    for t in ("Your Hoola,\\nready when you are.", "Continue with Google", "Continue with email", "Check your email",
              "class _CodeBoxes", "Open Gmail", "Send a new code in", "What should Hoola call you?", "Start using Hoola",
              "HoolaMark(", "HoolaFont.serif", "hoolaTheme(b)", "_pickLanguage"):
        assert t in d, t
    assert "withValues(" not in d                        # Flutter 3.24 on CI has withOpacity, not withValues
    assert "LiveSantosh" not in d and "Aurora(" not in d


def test_browser_walk_email_sign_up(arena_server, monkeypatch):
    base, browser, _key = arena_server
    from app.config import get_settings
    from app import emailauth as EA
    from app.site import sitemail as SM
    monkeypatch.setattr(get_settings(), "site_mail_provider", "capture")
    SM.CAPTURED.clear()
    EA._RATE.clear()
    for w, h in ((1280, 820), (390, 844)):
        p = browser.new_page(viewport={"width": w, "height": h})
        errs: list[str] = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.goto(base + "/console/")
        p.wait_for_selector("#lstep1:not([hidden])")
        assert p.is_visible(".lg-side") == (w > 900)
        assert p.evaluate("document.documentElement.scrollWidth") <= w
        if w > 900:                                 # v0.999.179: the left side's words sit centred, not hugging the edge
            gap = p.evaluate("""() => { const s = document.querySelector('.lg-side').getBoundingClientRect();
                return ['.lg-pitch', '.lg-moment', '.lg-works'].map(q => {
                    const e = document.querySelector('.lg-side ' + q).getBoundingClientRect();
                    return [Math.round(e.left - s.left), Math.round(s.right - e.right)]; }); }""")
            for left, right in gap:
                assert abs(left - right) <= 3, gap
        addr = f"asha{w}@gmail.com"
        p.fill("#lemail", addr)
        p.click("#ebtn")
        p.wait_for_selector("#lstep2:not([hidden])")
        assert addr in p.text_content("#lsent") and p.is_visible("#lgmail")
        assert "0:3" in p.text_content("#lresend") or "0:2" in p.text_content("#lresend")
        code = re.search(r"\b(\d{6})\b", SM.CAPTURED[-1]["body"]).group(1)
        p.fill("#lcode", code)                      # six digits = it goes by itself
        p.wait_for_selector("#lstep3:not([hidden])")
        p.fill("#lname", "Asha Rao")
        assert "Good to meet you, Asha." in p.text_content("#lgreet")
        p.click("#nbtn")
        p.wait_for_selector("#login", state="hidden")
        assert not errs, errs
        p.close()
