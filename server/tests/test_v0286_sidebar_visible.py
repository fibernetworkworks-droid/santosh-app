"""v0.286 SIDEBAR FULLY VISIBLE: section labels were 12px / 400 in the faint --dim grey (the "hidden" look); now the
labels are 13px / 500 in --mut, chat titles 14px / 470 and nav rows 14px / 500 in the ink - Claude's medium weight."""
from __future__ import annotations

import re
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "v2.css").read_text()


def _block() -> str:
    return CSS[CSS.index("v0.286 SIDEBAR FULLY VISIBLE"):]


def test_last_word_on_the_sidebar():
    b = _block()
    assert "#app .side .sn,#app .side .sn .txt,#app .side .newc .txt{font-weight:500;color:var(--ink)}" in b
    assert "#app .side .rc,#app .side .rct{font-size:14px;font-weight:470;color:var(--ink)}" in b
    assert ("#app .side .slabel,#app .side .rg,#app .side .sgh .sgn{font-size:13px;font-weight:500;letter-spacing:0;"
            "text-transform:none;color:var(--mut)}") in b
    assert "#app .side .rcarch{font-size:13px;font-weight:450;color:var(--mut)}" in b
    # nothing after this block takes the sidebar back to the thin / faint values
    assert "v0.286 SIDEBAR FULLY VISIBLE" in CSS[-9000:]


def test_type_rules_kept():
    b = _block()
    assert not re.search(r"font-weight:\s*(6[0-9][1-9]|[7-9]\d\d)", b)            # nothing over 600 (v0.255)
    assert not re.search(r"font-size:\s*(9|10|11)(\.\d+)?px", b)                   # nothing under 12px
    assert "var(--dim)" not in b                                                    # the faint grey is gone from the sidebar


def test_variable_font_carries_the_in_between_weights():
    html = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "v2.html").read_text()
    assert "Schibsted+Grotesk:wght@400..700" in html


def test_premium_pass():
    b = _block()
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "chatlist.js").read_text()
    ws = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "workspace.js").read_text()
    # line icons instead of emoji chrome; her own session emoji is kept
    assert "🗄 Show archived" not in js and ">⋯</button>" not in js and "${IC.archive}<span>Show archived</span>" in js
    assert "const secIcon = p => p.emoji && p.emoji !== '📁'" in js
    # one row rhythm, the ⋯ inside the pill, the session as a row
    assert "#app .side .rc{min-height:34px;padding:7px 8px 7px 10px;border-radius:8px}" in b
    assert "#app .side .rcm{position:absolute;right:4px;top:50%;margin-top:-14px}" in b
    assert "#app .side .sgh .sgn{font-size:14px;font-weight:500;color:var(--ink);gap:9px}" in b
    # a wider default sidebar (Claude ~288): 224 cut every title at ~20 characters
    assert "let width=272,drag=null;" in ws and "set(272)" in ws
    assert "var(--sidebar-width,224px)" not in CSS
