"""v0.555 HOOLA CARD - the owner approved the premium card design ("BUILD THIS",
claude.ai/artifact/NgbT6WLDj63Jhh7MbysuGD). The default card - every card kind with no screen of its own - now has one
anatomy on both surfaces: eyebrow (desk + time), tile, title + status signal (dot + plain words), one sentence, the
amount as the hero, receipt facts, step segments, a secure band for money, a docked action. Console: hcard.js (pure,
run here with node). Phone: lib/ui/any_card.dart (the same rules; compiled on CI)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CON = ROOT / "app" / "static" / "console"
DART = ROOT.parent / "lib" / "ui" / "any_card.dart"

node = shutil.which("node")
needs_node = pytest.mark.skipif(not node, reason="node is not installed")


def _js(expr: str):
    code = ("const H=require(" + json.dumps(str(CON / "hcard.js")) + ");"
            "process.stdout.write(JSON.stringify(" + expr + "));")
    out = subprocess.run([node, "-e", code], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@needs_node
def test_states_read_in_plain_words():
    assert _js("['pending','running','ready','failed','cancelled',''].map(s=>H.stateOf({status:s}))") == \
        ["ask", "work", "done", "failed", "stopped", "done"]
    html = _js("H.html('game_desk',{id:'g1',status:'ready',title:'Runner game',say:'Build 3 playtested'},null,{})")
    assert "Ready" in html and "Runner game" in html and "Build 3 playtested" in html and "t-ok" in html
    assert "READY" not in html                                        # never a raw status code


@needs_node
def test_internal_codes_never_show_and_facts_are_capped():
    html = _js("H.html('eng_project',{id:'e1',job_id:'gd_8f2a91c',tenant:'t1',conversation_id:'c1',status:'ready',"
               "title:'Bracket',material:'PLA',mass:'42 g',parts:'3',extra:'x',more:'y'},null,{})")
    for leak in ("gd_8f2a91c", "t1", "c1"):
        assert leak not in html
    assert html.count("<dt>") == 3 and "Material" in html


@needs_node
def test_a_money_ask_is_the_hero_with_the_secure_band():
    html = _js("H.html('bill_pay',{id:'b1',status:'pending',title:'Bijli bill',amount_paise:124000,pay_method:'UPI'},null,{})")
    assert "t-money" in html and "1,240" in html and "<sup>₹</sup>" in html
    assert "fingerprint" in html and "Never by voice" in html
    assert _js("[H.amountOf({amount:'124000'}),H.amountOf({amount:'₹1,24,000'}),H.amountOf({amount_paise:124050})]") == \
        ["1,24,000", "1,24,000", "1,240.50"]                         # Indian grouping, paise as two digits


@needs_node
def test_progress_is_step_segments():
    html = _js("H.html('research_run',{id:'r1',status:'running',name:'Mithai market',step:4,total:6},null,{})")
    assert html.count('<i class="on">') == 4 and html.count('<i class="now">') == 1 and "4 / 6" in html


@needs_node
def test_the_dock_only_when_there_is_somewhere_to_go_and_text_is_escaped():
    assert "hcard-dock" not in _js("H.html('x_card',{status:'ready',title:'A'},null,{})")
    assert "data-pn" in _js("H.html('x_card',{status:'ready',title:'A'},null,{panel:true})")
    html = _js("H.html('x_card',{status:'ready',title:'<img src=x onerror=alert(1)>'},null,{link:'https://e.x'})")
    assert "<img" not in html and "&lt;img" in html and 'href="https://e.x"' in html


def test_console_uses_it_as_the_default_card():
    app = (CON / "app.js").read_text()
    assert "window.HoolaCard.html(kind, p, at, {label: LABEL[kind] || '', link, panel: !!pit, told: !!p.told_on_call})" in app
    assert "el.querySelector('[data-pn]')?.addEventListener('click', () => PN.open(pit));" in app   # open beside chat kept
    html = (CON / "v2.html").read_text()
    assert html.index("console/hcard.js") < html.index("console/results.js") < html.index("console/workspace.js")
    css = (CON / "v2.css").read_text()
    for sel in (".cd.cd-h", ".hcard-eb", ".hcard-st i", ".hcard-rc dt", ".hcard-steps i.now", ".hcard-sec", ".hcard-dock"):
        assert sel in css, sel
    block = css[css.index("v0.555 HOOLA CARD"):]
    assert "#" not in block.split("{", 1)[1].replace("#app", ""), "the card CSS uses theme tokens only (no literal colours)"


def test_phone_card_has_the_same_anatomy():
    d = DART.read_text()
    for piece in ("static String stateOf", "static bool isMoney", "static String amountOf", "'Needs your OK'",
                  "'Running'", "'Ready'", "Approve with fingerprint", "desk.toUpperCase()", "for (var i = 1; i <= 6; i++)",
                  "FontFeature.tabularFigures()", "launchUrl", "import 'dart:ui' show FontFeature;"):
        assert piece in d, piece
    chat = (ROOT.parent / "lib" / "ui" / "chat_screen.dart").read_text()
    assert "AnyEventCard(v: it.data, at: it.at)" in chat


@needs_node
def test_progress_fields_and_errors_never_become_facts():
    html = _js("H.html('research_run',{status:'running',name:'M',step:4,total:6,pages_read:23},null,{})")
    assert "<dt>Step" not in html and "<dt>Total" not in html and "<dt>Pages read" in html
    html = _js("H.html('agent_team',{status:'failed',title:'T',error:'Two agents timed out'},null,{})")
    assert "Two agents timed out" in html and "<dt>Error" not in html and "t-bad" in html
