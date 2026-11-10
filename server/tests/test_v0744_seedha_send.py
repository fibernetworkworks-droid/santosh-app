"""v0.744 SEEDHA SEND (owner screenshot: "REMOVE THE AVATAR FACE AND CHAT PANEL SEND BUTTON IS GOING OUT OF PANEL"):
the v0.740 model chip could not shrink, so Send sat 12px past the composer edge; the home avatar face is hidden."""
from __future__ import annotations

import json

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

CH = {"available": True, "reason": "", "selected": "aihubmix:coding-glm-5.3-flash-free", "models": [
    {"id": "aihubmix:coding-glm-5.3-flash-free", "name": "GLM 5.3 Flash (AIHubMix)", "provider": "AIHubMix",
     "free": True, "reads": ["text", "image"], "tools": True, "context": 200000, "default": True, "selected": True,
     "pickable": True, "note": ""}]}


def test_send_inside_the_box_and_no_avatar_face(arena_server):  # noqa: F811
    base, browser, key = arena_server
    for w in (1440, 1180, 1000, 760):
        ctx = browser.new_context(viewport={"width": w, "height": 860})
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()

        def config(route):
            r = route.fetch(); d = r.json(); d["human"] = True
            route.fulfill(response=r, body=json.dumps(d))
        pg.route("**/api/console/config", config)
        pg.route("**/api/model/choices", lambda r: r.fulfill(json=CH))
        pg.goto(base + "/console/")
        pg.wait_for_selector("#modelBtn:not([hidden])")
        pg.wait_for_timeout(300)
        m = pg.evaluate("""()=>{const c=document.getElementById('composer').getBoundingClientRect(),
            s=document.getElementById('sendBtn').getBoundingClientRect(),
            h=document.querySelector('.landing .halo');
            return {cr:c.right, sr:s.right, sl:s.left, cl:c.left, halo: !!(h && h.offsetParent)}}""")
        assert m["sr"] <= m["cr"] - 2 and m["sl"] >= m["cl"], (w, m)       # Send fully inside the typing box
        assert m["halo"] is False, (w, m)                                  # no avatar face on the home
        ctx.close()
