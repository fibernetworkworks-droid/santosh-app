"""v0.286 SIDEBAR FULLY VISIBLE: section labels were 12px / 400 in the faint --dim grey (the "hidden" look); now the
labels are 13px / 500 in --mut, chat titles 14px / 450 and nav rows 14px / 500 in the ink - Claude's medium weight."""
from __future__ import annotations

import re
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "v2.css").read_text()


def _block() -> str:
    return CSS[CSS.index("v0.286 SIDEBAR FULLY VISIBLE"):]


def test_last_word_on_the_sidebar():
    b = _block()
    assert "#app .side .sn,#app .side .sn .txt,#app .side .newc .txt{font-weight:500;color:var(--ink)}" in b
    assert "#app .side .rc,#app .side .rct{font-size:14px;font-weight:450;color:var(--ink)}" in b
    assert ("#app .side .slabel,#app .side .rg,#app .side .sgh .sgn{font-size:13px;font-weight:500;letter-spacing:0;"
            "text-transform:none;color:var(--mut)}") in b
    assert "#app .side .rcarch{font-size:13px;font-weight:450;color:var(--mut)}" in b
    # nothing after this block takes the sidebar back to the thin / faint values
    assert "v0.286 SIDEBAR FULLY VISIBLE" in CSS[-4000:]


def test_type_rules_kept():
    b = _block()
    assert not re.search(r"font-weight:\s*(6[0-9][1-9]|[7-9]\d\d)", b)            # nothing over 600 (v0.255)
    assert not re.search(r"font-size:\s*(9|10|11)(\.\d+)?px", b)                   # nothing under 12px
    assert "var(--dim)" not in b                                                    # the faint grey is gone from the sidebar


def test_variable_font_carries_the_in_between_weights():
    html = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "v2.html").read_text()
    assert "Schibsted+Grotesk:wght@400..700" in html
