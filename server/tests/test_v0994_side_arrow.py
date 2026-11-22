"""v0.994 SIDE ARROW (owner, her screenshot of "Reading the web page 3m 49s ⌄": "CHECK THE DOWN ARROW --- IN LOADING MAKE
IT HORIZONTAL DURING WORK. WHEN USER CLICK ON IT IT GETS DOWN"): the arrow beside the working row (and the "Worked for"
row) points right while folded and turns down when she opens the steps."""
from __future__ import annotations

from pathlib import Path

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

CON = Path(__file__).resolve().parents[1] / "app/static/console"


def test_the_arrow_rules():
    css = (CON / "v2.css").read_text()
    assert "#app .simple-progress .wtog .hm-dn,#app .tools.hmfold>summary .hm-dn{transform:rotate(-90deg)}" in css
    assert "#app .simple-progress.wopen .wtog .hm-dn,#app .tools.hmfold[open]>summary .hm-dn{transform:none}" in css
    assert "{transform:rotate(180deg)}" not in css.split("SIDE ARROW")[1][:600]


def test_right_while_working_down_when_opened(arena_server):
    import httpx
    from app.db import Message, session
    from app.events import bus
    base, browser, key = arena_server
    h = {"Authorization": f"Bearer {key}"}
    cid = httpx.post(base + "/api/conversations", headers=h, timeout=20).json()["id"]
    with session() as s:
        s.add(Message(conversation_id=cid, role="user", content="Give me a 50 bank list",
                      display="Give me a 50 bank list", in_history=True))
        s.commit()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/")
    pg.get_by_text("Give me a 50 bank list").first.click()
    pg.wait_for_timeout(1500)
    for kind, p in (("typing", {"on": True}),
                    ("step", {"id": "s1", "tool": "web_fetch", "label": "Reading the web page", "state": "running"})):
        bus.publish(cid, kind, p)
        pg.wait_for_timeout(400)
    pg.wait_for_timeout(600)
    angle = """()=>{const m=getComputedStyle(document.querySelector('.simple-progress .wtog .hm-dn')).transform;
      if(!m||m==='none')return 0;const v=m.match(/matrix\\(([^)]+)\\)/)[1].split(',').map(Number);
      return Math.round(Math.atan2(v[1],v[0])*180/Math.PI)}"""
    folded = pg.evaluate(angle)
    pg.click(".simple-progress .wtog")
    pg.wait_for_timeout(450)
    opened = pg.evaluate(angle)
    ctx.close()
    assert folded == -90, folded       # points right while it works
    assert opened == 0, opened         # turns down when she opens it
    assert not errs, errs


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.150"
    assert "0.999.150+1145" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
