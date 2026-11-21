"""v0.999.89 D8 wave 8: live chat with her team and her clinic's live queue on a React website - the same chat and queue
as her HTML website (her website's own member app on Hoola). A signed-in visitor writes to her team and sees replies
arrive live; her staff see every conversation and reply. The queue board shows only numbers and updates by itself; a
signed-in patient takes today's token and sees how many are ahead; her staff call the next token. Tokens are given on
Hoola's server under its lock."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.appengine import rules as RL
from app.appengine import service as AE
from app.appengine import writer as W
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v0999_82_own_address import HOST, _on  # noqa: F401  (autouse fixture)
from tests.test_v0999_82_signin import _portal
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

TPL = Path(AE.__file__).resolve().parent / "template"
SITE = {"id": "site_abc123", "app": {"lists": [{"key": "orders", "label": "Orders"}], "queue": {"label": "OPD queue"}}}


# ---------------------------------------------------------------- 1. by code
def test_chat_on_every_page_and_the_queue_where_she_switched_it_on():
    ctx = W.Ctx("Sunrise Clinic", _portal(), {"phone": "+91 90000 00001", "_site": SITE}, "s", None)
    lay = W.layout_file(ctx)
    assert 'import LiveChat from "@/islands/LiveChat";' in lay and 'site="site_abc123"' in lay and 'signin="./sign-in"' in lay
    home, rows = W.page_file(_portal()[0], ctx, {})
    assert 'import QueueBoard from "@/islands/QueueBoard";' in home and 'label="OPD queue"' in home
    assert home.index('data-sec="home:0"') < home.index("<QueueBoard ") < home.index('data-sec="home:1"')   # after the hero
    app, rows2 = W.page_file(_portal()[2], ctx, {})
    assert app.index("<QueueBoard ") < app.index('data-sec="my-orders:0"')                               # top of her app page
    sign, _ = W.page_file(_portal()[1], ctx, {})
    assert "QueueBoard" not in sign
    kit = W.kit_files(rows + rows2, False, chat=True)
    assert {"src/islands/LiveChat.tsx", "src/islands/QueueBoard.tsx"} <= set(kit)
    # no queue switched on: no board; no member app: no chat either
    noq = W.Ctx("x", _portal(), {"_site": {"id": "site_abc123", "app": {"lists": [{"key": "orders", "label": "Orders"}]}}}, "s", None)
    assert "QueueBoard" not in W.page_file(_portal()[0], noq, {})[0] and "LiveChat" in W.layout_file(noq)
    bare = W.Ctx("x", _portal(), {"_site": {"id": "site_abc123"}}, "s", None)
    assert "LiveChat" not in W.layout_file(bare) and "QueueBoard" not in W.page_file(_portal()[0], bare, {})[0]
    assert "src/islands/LiveChat.tsx" not in W.kit_files([], False)


def test_both_islands_keep_the_rules_and_never_touch_the_token():
    from app.appengine import image as IMG
    deps = set(IMG.project_package("x").get("dependencies") or {})
    for f in ("src/islands/LiveChat.tsx", "src/islands/QueueBoard.tsx"):
        t = (TPL / f).read_text()
        assert RL.check_file(f, t, deps) == [], (f, RL.check_file(f, t, deps))
        assert "localStorage" not in t and "Authorization" not in t, f
    member = (TPL / "src" / "lib" / "member.ts").read_text()
    assert "export function liveStream" in member and "Authorization: `Bearer ${tok}`" in member
    assert "src/lib/member.ts" in RL.LOCKED
    q = (TPL / "src" / "islands" / "QueueBoard.tsx").read_text()
    assert "/queue/live" in q and "never by this page" in q


def test_the_checklist_ticks_live_chat_and_the_queue():
    from app.appengine import parity
    st = {x["key"]: x for x in parity.check()["rows"]}
    assert st["live"]["state"] == "works", st["live"]
    assert st["push"]["state"] == "not yet"


# ---------------------------------------------------------------- 2. a real clinic website, live on its own address
@pytest.fixture
def live_clinic(ae_env, monkeypatch):
    _box()
    from app.net import booking as BK
    from app.site import ai as AI
    from app.site import applink as AL
    from app.site import livesite as LS
    from app.site import prototype as PT
    from app.site import service as S
    from app.site import webapp as WA
    from tests.test_v0305_web_apps import DESIGN
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))
    monkeypatch.setattr(BK, "free_slots", lambda tenant, n=12: ["2030-01-07T10:00"][:n])
    monkeypatch.setattr(BK, "say_slot", lambda tenant, iso: "Mon 7 Jan, " + iso[-5:])
    real = AI.ask_json

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(WA.DESIGN_SYSTEM[:40]):
            return json.loads(json.dumps(DESIGN))
        return real(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    v = S.new(T, "A website for Sunrise Bakery in Pune: breads, cakes, order online.", name="Sunrise Bakery",
              answers={"phone": "9876543210", "address": "12, Shanti Complex, Pune", "email": "hello@sunrise.example"})
    S.design_app(T, v["id"], "customers place and track their orders")
    WA._RATE.clear()
    LS.save_cfg(AL.project(S._load(v["id"])), {"on": True, "label": "Pickup queue", "self_take": True, "open": True})
    PT._write_version(S._load(v["id"]), _portal(), "test", "hoola")
    PT.approve(T, v["id"], PT.meta(S._load(v["id"]))["hash"])
    out = S.view(S._load(v["id"]))
    assert out["status"] == "ready", out.get("error")
    return v["id"]


def _server():
    """The real server (uvicorn), so the live streams really stream; Chromium reaches it by her address's own name."""
    import threading
    import time
    import uvicorn
    from app import main
    from tests.test_v161_console_e2e import _free_port
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    assert srv.started
    return srv, port


def test_a_patient_takes_a_token_and_chats_with_her_team(live_clinic):
    from playwright.sync_api import sync_playwright
    from app.appengine import speed as SP
    from app.main import app
    from app.site import service as S
    sid = live_clinic
    c = TestClient(app)
    card = c.post(f"/api/sites/{sid}/launch-request", json={}).json()
    assert not card["blockers"], card["blockers"]
    assert c.post(f"/api/sites/{sid}/launch", json={"hash": card["hash"]}).status_code == 200
    base_api = f"/api/site-app/{sid}"
    board = c.get(f"{base_api}/queue", headers={"host": HOST}).json()
    assert board["on"] is True and board["label"] == "Pickup queue" and "name" not in json.dumps(board)
    asha = c.post(f"{base_api}/signup", json={"email": "asha@x.in", "password": "asha-pass-1", "name": "Asha", "consent": True}).json()
    ravi = c.post(f"{base_api}/signup", json={"email": "ravi@x.in", "password": "ravi-pass-1", "name": "Ravi", "consent": True}).json()
    rid = c.get(f"{base_api}/me", headers={"Authorization": "Bearer " + ravi["token"]}).json()["me"]["id"]
    assert S.app_role(T, sid, rid, "staff")["role"] == "staff"
    assert c.get(f"{base_api}/me", headers={"Authorization": "Bearer " + ravi["token"]}).json()["me"] is None   # a new role ends old sign-ins
    ravi = c.post(f"{base_api}/login", json={"email": "ravi@x.in", "password": "ravi-pass-1"}).json()
    staff = {"Authorization": "Bearer " + ravi["token"]}
    srv, port = _server()
    base = f"http://{HOST}:{port}"
    errors: list[str] = []
    try:
        with sync_playwright() as pw:
            import os
            b = pw.chromium.launch(args=[f"--host-resolver-rules=MAP {HOST} 127.0.0.1"],
                                   **({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "Error" in m.text else None)  # React logs a crashed island here
            pg.add_init_script(f"localStorage.setItem({json.dumps('hoola:member:' + sid)}, {json.dumps(asha['token'])})")
            pg.goto(base + "/", wait_until="load")
            qb = pg.locator('section[data-block="queue_board"]')
            qb.get_by_text("Pickup queue").wait_for(timeout=30000)
            qb.scroll_into_view_if_needed()
            pg.wait_for_function("""() => { const el = document.querySelector('section[data-block="queue_board"]').closest('[data-island]');
              return !!el && Object.keys(el).some((k) => k.startsWith('__reactContainer')); }""", timeout=30000)
            qb.get_by_role("button", name="Take a token").click(timeout=30000)
            qb.get_by_text("Your token").wait_for(timeout=15000)
            assert "1" in qb.locator("strong").first.inner_text()
            # her staff calls token 1: the board streams it and the patient's page says it is her turn - no reload
            assert c.post(f"{base_api}/queue/call", json={}, headers=staff).status_code == 200
            qb.get_by_text("it is your turn now").wait_for(timeout=30000)
            # chat: the patient writes, her staff replies, the reply arrives live in the open chat
            pg.get_by_role("button", name="Message Sunrise Bakery").click(timeout=30000)
            dlg = pg.get_by_role("dialog", name="Message Sunrise Bakery")
            dlg.get_by_label("Write a message").fill("Is my cake ready?")
            dlg.get_by_role("button", name="Send").click()
            dlg.get_by_text("Is my cake ready?").wait_for(timeout=15000)
            aid = c.get(f"{base_api}/me", headers={"Authorization": "Bearer " + asha["token"]}).json()["me"]["id"]
            th = c.get(f"{base_api}/chat?all=1", headers=staff).json()["threads"]
            assert [t["member"] for t in th] == [aid] and th[0]["last"] == "Is my cake ready?"
            assert c.post(f"{base_api}/chat/{aid}", json={"text": "Yes, ready at 5 pm."}, headers=staff).status_code == 200
            dlg.get_by_text("Yes, ready at 5 pm.").wait_for(timeout=30000)           # live, the dialog never closed
            b.close()
    finally:
        srv.should_exit = True
    assert not errors, errors
