"""v0.283 MENUS LIKE CLAUDE: one dropdown (console/menu.js) for the chat ⋯ menus, export and the new account menu;
the Create Studio pickers and the / list take the same look."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _r(n: str) -> str:
    return (CON / n).read_text()


def test_menu_module():
    js = _r("menu.js")
    assert "window.HoolaMenu = (() => {" in js and "return {open, close, isOpen: () => !!M, icon};" in js
    for k in ("role', 'menu'", "menuitemradio", "aria-expanded", "ArrowDown", "Home", "End", "'Escape'", "'Tab'",
              "addEventListener('pointerdown', outside, true)", "if (M && M.anchor === anchor) { close(true); return null; }",
              "startsWith(k)", "danger", "msep", "class=\"mh\""):
        assert k in js, k
    r = subprocess.run(["node", "--check", str(CON / "menu.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_loaded_before_its_users():
    html = _r("v2.html")
    m = html.index("/static/console/menu.js?v=")
    assert m < html.index("/static/console/chatlist.js?v=") < html.index("/static/console/v2.js?v=")
    assert 'id="exportMenu"' not in html and 'id="cExportMenu"' not in html


def test_every_console_menu_uses_it():
    cl, v2 = _r("chatlist.js"), _r("v2.js")
    assert "HoolaMenu.open(btn, [" in cl and "cls: 'rmenu'" in cl and "{label: 'Delete', icon: 'trash', danger: true" in cl
    assert "MENU" not in cl                                   # the old hand-made menu is gone
    assert "$('#exportBtn').addEventListener('click', exportMenu);" in v2 and "$('#cShare').addEventListener('click', exportMenu);" in v2
    # the header ⋯ used to close itself on the same click (the list's outside-click handler); menu.js ignores its own button
    assert "CH?.menu(CONV, e.currentTarget, e.detail === 0)" in v2
    acc = v2[v2.index("$('#model').addEventListener('click'"):]
    acc = acc[:acc.index("});") + 3]
    for k in ("'Settings'", "'Light'", "'Dark'", "'System'", "'Keyboard shortcuts'", "'Log out'", "place: 'above'"):
        assert k in acc, k
    assert "window.HoolaMenu?.isOpen()" in v2                  # Esc peels the open menu first


def test_claude_look_is_crisp():
    css = _r("v2.css")
    blk = css[css.index("v0.283 MENUS LIKE CLAUDE"):]
    assert ".hmenu{" in blk and "border-radius:12px" in blk and "font:400 14px/20px var(--fb)" in blk
    assert "min-height:32px" in blk and ".hmenu .msep{" in blk and ".hmenu .mi.danger" in blk
    assert "backdrop-filter:blur" not in blk and "infinite" not in blk
    assert not re.search(r"font-weight:\s*(6[5-9]\d|[7-9]\d\d)", blk)
    assert not re.search(r"font-size:\s*(9|10|11)(\.\d+)?px", blk)
    assert ".rmenu{" not in css and ".xmenu{" not in css


def test_studio_picker_matches():
    css = _r("studio.css")
    pop = css[css.index(".pop{"):css.index("/* ---------- v0.262")]
    assert "border-radius:12px" in pop and "min-height:32px" in pop and ".pop .ptx b{font-weight:400;font-size:14px" in pop
    assert "background:var(--priSoft)" not in pop               # the choice is a tick, not a coloured row
