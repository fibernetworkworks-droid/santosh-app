"""v0.999.81 CUSTOMER SUPPORT DESK: the Customer Support employee's own section - hireable, its own chat (kind 'support',
kept out of her chat lists) with the desk block + the seva tools in view, the desk page, every Open desk door, and the
desk's pages walked in a real browser (answer a gap, approve drafts, open a ticket, reply, decide an exception)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)

T = "default"


@pytest.fixture
def sv(env, monkeypatch):
    from app.seva import service as S
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    from app import supportchat as SC
    SC._OF.clear()
    SC._BLOCK.clear()
    return S


def test_hire_chat_block_and_wiring(sv):
    from pathlib import Path
    from app import supportchat as SC
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert SC.summary(T) == {"hired": False}
    cat = {e["key"]: e for e in hire.catalog(T)}
    assert cat["support"]["live"] is True and cat["support"]["never"]
    hire.hire(T, "support", trust="seekh")
    d = SC.summary(T)
    assert d["hired"] and d["open"] == 0 and d["answers"] == 0
    assert [c["key"] for c in d["channels"]] == ["whatsapp", "hoola", "phone", "email", "web"]
    assert {c["key"]: c["state"] for c in d["channels"]}["web"] == "soon"     # never a made-up "connected"
    chat = SC.current(T)
    assert SC.is_support(chat["id"]) and SC.owns(T, chat["id"])
    assert SC.current(T)["id"] == chat["id"]
    assert "your knowledge is empty" in SC.greeting(T)
    blk = SC.block(T)
    assert "<support_desk>" in blk and "ONLY her tap" in blk and "never promise" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_spc.is_support(conversation_id)" in src and "adm.admit_families(_spc.FAMILIES)" in src
    from app.agent import admit
    assert set(SC.FAMILIES) <= set(admit.FAMILY_OF.values())
    for f in ("callconv.py", "convs.py"):
        assert '"telecall", "support")' in (root / "server/app" / f).read_text()
    from app.credits import wallet
    assert wallet.employee_of("seva") == "support" and wallet.employee_of("seva_dekho") == "support"
    from app.main import APP_VERSION, app
    c = TestClient(app)
    r = c.get("/console/support")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "supportdesk.js" in r.text
    html = (root / "server/app/static/console/supportdesk.html").read_text()
    for f in ("chatkit.js", "quality.js", "seodesk.css", "supportdesk.css", "supportdesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    assert "location.assign('/console/support')" in (root / "server/app/static/console/v2.js").read_text()
    assert "support: 'supportdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/support'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_support_chat_kept_out_of_her_chat_lists(sv):
    from app import callconv
    from app.db import Conversation, session
    from app.employee import hire
    from app import supportchat as SC
    from sqlalchemy import select
    hire.hire(T, "support", trust="seekh")
    cid = SC.new_chat(T)["id"]
    with session() as s:
        ids = [c.id for c in s.scalars(select(Conversation).where(Conversation.tenant_id == T, callconv.not_call())).all()]
    assert cid not in ids


def test_summary_counts_real_work(sv):
    from app import supportchat as SC
    from app.employee import hire
    S = sv
    hire.hire(T, "support", trust="seekh")
    S.kb_add(T, "What are your timings?", "10 am to 7 pm, Monday to Saturday.")
    S.kb_import(T, text="Q: Is there a deposit?\nA: Rs 1,000 for the router, returned when you leave.")
    t = S.new_ticket(T, "Internet not working since morning, urgent", "phone", name="Rahul", phone="9811112222")
    S.exception_request(T, "refund", "size was wrong", 1299, t["number"])
    S.answer(T, "do you give EMI on the yearly plan?", "whatsapp", "wa:919811112222")
    SC.forget(T)
    d = SC.summary(T)
    assert d["open"] == 1 and d["waiting"] == 1 and d["answers"] == 1 and d["drafts"] == 1 and d["gaps"] == 1
    blk = SC.block(T)
    assert "Open tickets: 1" in blk and "1 exceptions" in blk


@pytest.fixture
def sp_server(sv, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    S = sv
    from app.employee import hire
    hire.hire(T, "support", trust="seekh")
    S.kb_add(T, "What are your timings?", "10 am to 7 pm, Monday to Saturday.")
    S.kb_import(T, text="Q: Is there a deposit?\nA: Rs 1,000 for the router, returned when you leave.")
    S.answer(T, "do you give EMI on the yearly plan?", "whatsapp", "wa:919811112222")
    t = S.new_ticket(T, "Router red light after the visit", "phone", name="Rahul", phone="9811112222")
    S.exception_request(T, "goodwill", "fault came back the day after the visit", 0, t["number"])
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY, t["number"]
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_support_desk_in_a_real_browser(sp_server):
    base, browser, key, number = sp_server
    errors = []
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/support")
        pg.wait_for_selector("#sdTabs [data-tab='today']", timeout=20000)
        pg.wait_for_function("() => document.querySelector('#sdThread').innerText.includes('only from your own knowledge')", timeout=20000)
        pg.evaluate("document.querySelector('#sdChat').__keep = 1")
        for tab, want in (("inbox", number), ("knowledge", "Drafts to check"), ("approvals", "Waiting for your yes"),
                          ("reports", "Why customers wrote"), ("settings", "Where customers reach you"), ("today", "Needs you")):
            pg.click(f"#sdTabs [data-tab='{tab}']")
            try:
                pg.wait_for_function("(w) => document.querySelector('#spPage').innerText.includes(w)", arg=want, timeout=10000)
            except Exception:
                raise AssertionError(f"{tab}: errors={errors} page={pg.inner_text('#spPage')[:500]!r}")
            assert pg.evaluate("document.querySelector('#sdChat').__keep") == 1
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        ctx.close()
    # then the work, once: answer a gap, approve drafts, ask as a customer, a ticket note + solved, decide an exception
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    # answer a question the knowledge could not answer
    pg.goto(base + "/console/support#/knowledge")
    pg.wait_for_selector("form.spGap input[name=answer]")
    pg.fill("form.spGap input[name=answer]", "Yes, in 3 or 6 months on any card.")
    pg.click("form.spGap button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('in 3 or 6 months')", timeout=10000)
    # approve the draft read from her text
    pg.click("#spApprove button[type=submit]")
    pg.wait_for_function("() => !document.querySelector('#spApprove')", timeout=10000)
    # ask as a customer
    pg.fill("#spTest input[name=question]", "what are your timings")
    pg.click("#spTest button[type=submit]")
    pg.wait_for_function("() => (document.querySelector('#spTestLine') || {innerText: ''}).innerText.includes('10 am to 7 pm')", timeout=10000)
    # one ticket: a note, then solved
    pg.goto(base + f"/console/support#/ticket/{number}")
    pg.wait_for_selector("#spNote input[name=text]")
    pg.fill("#spNote input[name=text]", "Line fault in sector 12")
    pg.click("#spNote button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Line fault in sector 12')", timeout=10000)
    pg.select_option("#spUpdate select[name=status]", "resolved")
    pg.click("#spUpdate button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Solved')", timeout=10000)
    # decide the waiting exception
    pg.goto(base + "/console/support#/approvals")
    pg.wait_for_selector("[data-decide][data-yes='1']")
    pg.click("[data-decide][data-yes='1']")
    pg.wait_for_function("() => !document.querySelector('[data-decide]')", timeout=10000)
    ctx.close()
    assert not errors, errors
