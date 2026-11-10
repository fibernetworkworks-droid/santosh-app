"""v0.726 PAGE CARD NARROW (owner, screenshot: "CHECK WHEN SIDE SECTION WIDTH MOVES --- THE CARD GET MESSY"): with the
side panel open the chat column is ~250-560 px while the window stays wide, so the v0.725 card (a viewport media query)
kept Share / Open on the right, squeezed the summary into a one-word column and the title to nothing. The card now
sizes by its OWN width (container query hpcard): buttons go to their own row under the text, the title wraps."""
from __future__ import annotations

from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CON = Path(__file__).resolve().parents[1] / "app/static/console"

_MEASURE = """()=>[...document.querySelectorAll('.hmpage')].map(e=>{const r=e.getBoundingClientRect();
  const b=x=>{const q=e.querySelector(x);return q?q.getBoundingClientRect():null};
  const t=b('.hp-title'),s=b('.hp-sub'),a=b('.hp-acts'),m=b('.hp-meta');
  const kids=[...e.querySelectorAll('*')].filter(k=>getComputedStyle(k).display!=='none'&&k.getClientRects().length)
    .map(k=>k.getBoundingClientRect()).filter(k=>k.width>0);
  return {w:r.width,title:t&&t.width,titleH:t&&t.height,sub:s&&s.width,metaBottom:m&&m.bottom,actsTop:a&&a.top,
    actsW:a&&a.width,out:kids.filter(k=>k.left<r.left-1||k.right>r.right+1).length}})"""


def test_card_sizes_by_its_own_width():
    css = (CON / "v2.css").read_text()
    assert "container-type:inline-size;container-name:hpcard" in css
    assert "@container hpcard (max-width:520px)" in css and "@container hpcard (max-width:340px)" in css
    assert "#app .hmpage .hp-acts{flex:0 0 100%}" in css


def test_card_intact_with_the_side_panel_open(arena_server):
    import httpx
    from app.db import Message, now, session
    from app.events import bus
    base, browser, key = arena_server
    h = {"Authorization": f"Bearer {key}"}
    cid = httpx.post(base + "/api/conversations", headers=h, timeout=20).json()["id"]
    with session() as s:
        s.add(Message(conversation_id=cid, role="user", content="NETMITRA UI DIKHAO", display="NETMITRA UI DIKHAO",
                      in_history=True))
        s.commit()
    summary = ("Demo dashboard for a small Indian ISP covering tickets, renewals, churn, outages, OLTs, staff and "
               "subscribers.")
    for w in (1180, 1280, 1440, 1700):
        ctx = browser.new_context(viewport={"width": w, "height": 900})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "/console/")
        pg.get_by_text("NETMITRA UI DIKHAO").first.click()
        pg.wait_for_timeout(1200)
        p = {"title": "NetMitra Ops Copilot", "version": 1, "error": "", "shared": False, "now": now().isoformat(),
             "started_at": now().isoformat()}
        bus.publish(cid, "artifact", {**p, "id": f"art_r{w}", "status": "ready", "stage": "done", "build_s": 47,
                                      "summary": summary})
        bus.publish(cid, "artifact", {**p, "id": f"art_b{w}", "status": "building", "stage": "writing",
                                      "build_s": None, "summary": ""})
        pg.wait_for_timeout(600)
        pg.evaluate("document.getElementById('app').classList.add('pn')")
        pg.wait_for_timeout(400)
        cards = pg.evaluate(_MEASURE)
        ctx.close()
        assert not errs, (w, errs)
        assert len(cards) >= 2, (w, cards)
        for c in cards[-2:]:
            assert c["out"] == 0, (w, c)                          # nothing sticks out of the card
            assert c["title"] >= 80, (w, c)                       # the name is readable
            assert c["sub"] >= min(200, c["w"] - 40), (w, c)      # the text gets the card's width
            if c["w"] <= 520:
                assert c["actsTop"] >= c["metaBottom"] - 1, (w, c)   # buttons on their own row under the text
