"""v0.226 CONSOLE R6 - phone width, motion, accessibility, checks. Scrollable views take keyboard focus, focus is always
visible, phone tap targets are at least 36px, her message toolbar sits under the text on a phone, smooth scrolling
turns off under reduced motion, every view has an English label, and Today survives a partial server answer."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "server" / "app" / "static" / "console"


def _read(name: str) -> str:
    return (CONSOLE / name).read_text()


def test_views_are_labelled_and_focusable():
    html = _read("v2.html")
    pads = re.findall(r'<div class="pad" id="(\w+)"([^>]*)>', html)
    assert len(pads) >= 6 and all('tabindex="0"' in a for _, a in pads), pads
    labels = re.findall(r'<section class="view" id="v-\w+" aria-label="([^"]+)"', html)
    for gone in ("Kaam", "Main", "Folder", "Creative workspace"):
        assert gone not in labels, gone
    for want in ("Tools", "Account", "Session", "Create", "Today"):
        assert want in labels, want


def test_reduced_motion():
    js = _read("v2.js")
    assert "const SMOOTH = () => matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';" in js
    assert "behavior: 'smooth'" not in js
    css = _read("v2.css")
    assert "@media(prefers-reduced-motion:reduce){#app *,#app *:before,#app *:after{animation:none!important;transition:none!important" in css


def test_focus_and_phone_targets():
    css = _read("v2.css")
    tail = css[css.index("v0.226 R6: phone width, motion, accessibility"):]
    for rule in ("#app :is(button,a,select,input,textarea,[tabindex]):focus-visible{outline:2px solid var(--saffron)",
                 "#app .cw-link{min-height:32px", "#app .ra{min-height:36px", "#app .ua{min-width:36px;min-height:36px}",
                 "#app .qc{min-width:36px;min-height:36px}", "#app .mu .utbar{position:static;opacity:1"):
        assert rule in tail, rule
    assert css.count("{") == css.count("}")


def test_today_survives_a_partial_answer():
    js = _read("v2.js")
    assert "d.reminders ||= []; d.lists ||= {}; d.pending ||= [];" in js


def test_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.323.0"
    assert "0.323.0+363" in (ROOT / "pubspec.yaml").read_text()
