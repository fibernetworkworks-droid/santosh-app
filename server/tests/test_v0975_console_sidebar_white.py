"""v0.975 SIDEBAR LIKE CLAUDE + FULL WHITE (owner: her Claude and Hoola sidebar screenshots - "same font, size, dark
word type for all" - and "Claude chat background is full white, make same for Hoola chat" -> design canvas
claude.ai/artifact/QMSQEVcnpFv4aHq6JTJ4aL boards 10-12 -> "GO BUILD"): rows 14 px / 500 / 32 px in one dark ink,
18 px icons, chats 14 px, labels 12 px grey, Pinned folded above Sessions and Recents, Recents folds, and in light
the page pure white with a near-white sidebar."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
CSS = (CON / "appdesign.css").read_text(encoding="utf-8")
CL = (CON / "chatlist.js").read_text(encoding="utf-8")


def test_shape():
    assert "--bg:#FFFFFF; --side-bg:#FAFAF9;" in CSS and "--side-ink:#141413" in CSS
    assert CSS.count("--side-ink:#F2F1EC") == 2          # both dark blocks
    assert "hoola.side.v1" in CL and "data-side=\"pinned\"" in CL
    block = CSS[CSS.index("v0.975 SIDEBAR LIKE CLAUDE"):]
    for line in block.splitlines():
        if "{" in line and not line.lstrip().startswith(("/*", "*", "@media")):
            assert line.lstrip().startswith(("html.appd", "html:not(.appd)")), line


def test_sidebar_and_white_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))

        def config(route):
            r = route.fetch(); d = r.json(); d["app_design"] = True; d["human"] = True
            route.fulfill(response=r, body=json.dumps(d))
        pg.route("**/api/console/config", config)
        pg.goto(base + "/console/")
        pg.wait_for_selector("html.appd #snav .sn")
        if scheme == "light":   # one pinned chat and one ordinary chat
            pg.evaluate(f"""async()=>{{const h={{'Authorization':'Bearer {key}','Content-Type':'application/json'}};
              for (const [t,p] of [['Hoola updates',true],['GST summary',false]]) {{
                const c=await (await fetch('/api/conversations',{{method:'POST',headers:h,body:'{{}}'}})).json();
                await fetch('/api/conversations/'+(c.id||c.conversation_id),{{method:'PATCH',headers:h,body:JSON.stringify({{title:t,pinned:p}})}});}}}}""")
            pg.reload(); pg.wait_for_selector("html.appd #snav .sn")
        pg.wait_for_timeout(800)
        m = pg.evaluate("""()=>{const q=s=>document.querySelector(s),g=(s,p)=>getComputedStyle(q(s))[p];
          const sn=q('#snav .sn');
          return {bg:getComputedStyle(document.body).backgroundColor, side:g('.side','backgroundColor'),
            rowH:sn.getBoundingClientRect().height, rowF:getComputedStyle(sn).fontSize, rowW:getComputedStyle(sn).fontWeight,
            rowC:getComputedStyle(sn).color, ic:sn.querySelector('svg').getBoundingClientRect().width,
            lab:g('.side > .slabel','fontSize'), labC:g('.side > .slabel','color'), rec:q('.side > .slabel').textContent.trim(),
            pin:q('#pinbox .plab')?.textContent.trim()||'', pinOpen:q('#pinbox .plab')?.getAttribute('aria-expanded'),
            pinFirst:!!(q('#pinbox')&&q('#projects')&&(q('#pinbox').compareDocumentPosition(q('#projects'))&4)),
            dayLabels:[...document.querySelectorAll('#recents .rg')].map(e=>e.textContent),
            chatF:q('#recents .rc')?getComputedStyle(q('#recents .rc')).fontSize:''}}""")
        assert m["rowH"] == 32 and m["rowF"] == "14px" and m["rowW"] == "500" and m["ic"] == 18, m
        assert m["lab"] == "12px" and m["rec"] == "Recents", m
        if scheme == "light":
            assert m["bg"] == "rgb(255, 255, 255)" and m["side"] == "rgb(250, 250, 249)", m
            assert m["rowC"] == "rgb(20, 20, 19)" and m["labC"] == "rgb(115, 114, 108)", m
            assert m["pin"] == "Pinned" and m["pinOpen"] == "false" and m["pinFirst"], m
            assert not any(d in ("Today", "Yesterday", "Pinned") for d in m["dayLabels"]), m
            assert m["chatF"] == "14px", m
            pg.click("#pinbox .plab"); pg.wait_for_timeout(200)
            assert pg.evaluate("[...document.querySelectorAll('#pinbox .rc')].map(e=>e.textContent.trim())") == ["Hoola updates"]
            pg.click(".side > .slabel[data-side=recents]"); pg.wait_for_timeout(200)
            assert pg.evaluate("getComputedStyle(document.querySelector('#recents')).display") == "none"
            pg.click(".side > .slabel[data-side=recents]"); pg.wait_for_timeout(200)
            assert pg.evaluate("getComputedStyle(document.querySelector('#recents')).display") != "none"
        else:
            assert m["bg"] == "rgb(20, 20, 19)" and m["rowC"] == "rgb(242, 241, 236)", m
        rows = pg.evaluate("[...document.querySelectorAll('#snav .sn > .txt')].map(e=>e.textContent)")
        assert rows[:3] == ["AI Employees", "Tools", "Computer"] and rows[-2:] == ["More", "Customize"], rows   # v0.976
        assert not {"Work", "AI Apps", "Arena"} & set(rows) and not any(r.startswith("Made by") for r in rows), rows
        pg.click(".side [data-more]"); pg.wait_for_timeout(300)
        items = pg.evaluate("[...document.querySelectorAll('[role=menu] [role^=menuitem]')].map(e=>e.textContent.trim())")
        assert any("Work" in t for t in items) and any("Docs and files" in t for t in items) and len(items) == 2, items
        if shots:
            pg.screenshot(path=f"{shots}/side-white-{scheme}.png")
        pg.keyboard.press("Escape")
        assert not errors, errors
        ctx.close()
