"""v0.999.158 BOOKS DESK: the Books & Accounts employee's own section like the business desks - its own chat (kind 'books',
kept out of her chat lists) with the desk block + the books tool in view, the business she picks, today's figures from her
books, every Open desk door, and the desk's pages walked in a real browser (set up a business, invoice, import a statement,
confirm the match, the month-end checklist, the exports)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def bk(env):
    from app import bookschat as BC
    BC._OF.clear()
    BC._BLOCK.clear()
    return BC


def _setup(name="Lumen Studio", cc="GB", cur="GBP", size="solo"):
    from app.fin import profile as PR
    pv = PR.preview({"size": size, "countries": [cc], "currency": cur, "name": name, "wants": ["books"]})
    return PR.apply(T, pv["answers"], pv["hash"])["id"]


def test_hire_chat_block_and_wiring(bk):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert bk.summary(T)["hired"] is False
    hire.hire(T, "books_accounts", trust="seekh")
    d = bk.summary(T)
    assert d["hired"] and d["workspace"] is None and d["businesses"] == []
    chat = bk.current(T)
    assert bk.is_books(chat["id"]) and bk.owns(T, chat["id"]) and bk.current(T)["id"] == chat["id"]
    assert "Set up your business" in bk.greeting(T)
    blk = bk.block(T)
    assert "<books_desk>" in blk and "never send an invoice" in blk and "No business set up yet" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_bkc.is_books(conversation_id)" in src and "adm.admit_families(_bkc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["books_accounts"] in bk.FAMILIES
    for f in ("callconv.py", "convs.py"):
        assert '"money", "books"' in (root / "server/app" / f).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/books")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "booksdesk.js" in r.text
    html = (root / "server/app/static/console/booksdesk.html").read_text()
    for f in ("chatkit.js", "quality.js", "seodesk.css", "moneydesk.css", "booksdesk.css", "booksdesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    assert "location.assign('/console/books')" in (root / "server/app/static/console/v2.js").read_text()
    assert "books_accounts: 'booksdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/books'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_books_chat_kept_out_of_her_chat_lists(bk):
    from sqlalchemy import select
    from app import callconv
    from app.db import Conversation, session
    from app.employee import hire
    hire.hire(T, "books_accounts", trust="seekh")
    cid = bk.new_chat(T)["id"]
    with session() as s:
        ids = [c.id for c in s.scalars(select(Conversation).where(Conversation.tenant_id == T, callconv.not_call())).all()]
    assert cid not in ids


def test_business_pick_and_numbers_from_the_books(bk):
    from app.employee import hire
    from app.fin import spine as SP
    from app.fin.desks import books as BK
    hire.hire(T, "books_accounts", trust="seekh")
    ws = _setup()
    _setup(name="Household", size="personal")          # a household is not a business: never offered here
    d = bk.summary(T)
    assert [b["name"] for b in d["businesses"]] == ["Lumen Studio"] and d["workspace"]["id"] == ws
    n = d["numbers"]
    assert n["currency"] == "GBP" and n["bank"] == 0 and n["bank_to_confirm"] == 0
    t = date.today()
    old = (t - timedelta(days=60)).isoformat()
    inv = BK.run(T, "invoice", {"workspace": ws, "party": "Northwind Ltd", "issue": old, "due": (t - timedelta(days=30)).isoformat(),
                                "lines": [{"description": "Retainer", "qty": 1, "price": 1000, "tax_pct": 20}], "issue_now": True})
    assert inv["number"]
    BK.run(T, "invoice", {"workspace": ws, "party": "Harbor Cafe", "lines": [{"description": "Menu", "price": 50}]})   # a draft
    SP.import_statement(T, ws, f"Date,Narration,Debit,Credit\n{t.isoformat()},NORTHWIND {inv['number']},,600.00\n{t.isoformat()},ADOBE CREATIVE CLOUD,56.98,\n", "Main account", "GBP")
    bk.forget(T)
    n = bk.summary(T)["numbers"]
    assert n["owed_to_you"] == 1200 and n["overdue_to_you"] == 1200 and n["drafts"] == 1
    assert n["bank_to_confirm"] == 2 and n["bank_sure"] == 1
    assert n["overdue_docs"][0]["party"] == "Northwind Ltd" and n["overdue_docs"][0]["days"] == 30
    assert n["month"]["profit"] >= 0 and n["close"]["of"] >= 5
    blk = bk.block(T)
    assert "Lumen Studio" in blk and "Bank lines to confirm: 2" in blk and inv["number"] in blk
    assert "Northwind" in bk.greeting(T) or "2 bank lines" in bk.greeting(T)
    with pytest.raises(bk.BooksDeskError):
        bk.pick(T, "someone-elses")
    ws2 = _setup(name="Second shop", size="business")
    assert bk.pick(T, ws2) == {"workspace": ws2} and bk.summary(T)["workspace"]["name"] == "Second shop"


def test_routes(bk):
    from app.main import app
    from app.employee import hire
    c = TestClient(app)
    assert c.get("/api/books/desk").json()["hired"] is False
    hire.hire(T, "books_accounts", trust="seekh")
    ws = _setup()
    d = c.get("/api/books/desk").json()
    assert d["workspace"]["id"] == ws and "numbers" in d
    assert c.put("/api/books/workspace", json={"workspace": "nope"}).status_code == 400
    assert c.put("/api/books/workspace", json={"workspace": ws}).json() == {"workspace": ws}
    r = c.post("/api/fin/books/invoice", json={"workspace": ws, "party": "Arden", "lines": [{"description": "Logo", "price": 300}]})
    assert r.status_code == 200, r.text
    chat = c.get("/api/books/chat").json()["id"]
    assert c.get(f"/api/books/chat/{chat}/ok").json() == {"ok": True}
    assert c.get("/api/books/chat/nope/ok").status_code == 404


@pytest.fixture
def bk_server(bk, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "books_accounts", trust="seekh")
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
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_books_desk_in_a_real_browser(bk_server, tmp_path):
    import os
    base, browser, key = bk_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    # no business yet: Settings opens, she sets one up (preview, then confirm)
    pg.goto(base + "/console/books")
    pg.wait_for_selector("form[data-form=setup]", timeout=20000)
    pg.wait_for_function("() => document.querySelector('#sdThread').innerText.includes('Set up your business')", timeout=20000)
    pg.fill("#bkSN", "Lumen Studio")
    pg.fill("#bkSC", "GB")
    pg.fill("#bkSK", "GBP")
    pg.click("form[data-form=setup] button[type=submit]")
    pg.wait_for_selector("[data-setupok]", timeout=10000)
    assert pg.input_value("#bkSN") == "Lumen Studio"
    pg.click("[data-setupok]")
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('In the bank')", timeout=15000)
    assert "Lumen Studio" in pg.inner_text("#bkSite")
    # a new invoice, issued
    pg.goto(base + "/console/books#/docs/new-sales")
    pg.wait_for_selector("#bkParty")
    pg.fill("#bkParty", "Northwind Ltd")
    pg.fill("#bkD0", "Website retainer")
    pg.fill("#bkP0", "1000")
    pg.click("[data-addline]")
    pg.fill("#bkD1", "Hosting")
    pg.fill("#bkP1", "200")
    assert pg.input_value("#bkParty") == "Northwind Ltd"          # adding a line keeps what she typed
    pg.click("form[data-form=doc] button[value=issue]")
    pg.wait_for_function("() => location.hash === '#/docs' && document.querySelector('#mdPage').innerText.includes('Northwind Ltd')", timeout=15000)
    page = pg.inner_text("#mdPage")
    assert "INV" in page or "-0001" in page, page[:400]
    num = pg.evaluate("document.querySelector('#mdPage tbody tr td').innerText").strip()
    # import a statement that pays it
    p = tmp_path / "stmt.csv"
    p.write_text(f"Date,Narration,Debit,Credit\n{date.today().isoformat()},NORTHWIND {num},,1200.00\n{date.today().isoformat()},ADOBE CREATIVE CLOUD,56.98,\n")
    pg.goto(base + "/console/books#/bank/import")
    pg.wait_for_selector("#bkFile")
    pg.set_input_files("#bkFile", str(p))
    pg.click("form[data-form=import] button[type=submit]")
    try:
        pg.wait_for_function("() => location.hash === '#/bank' && document.querySelector('[data-apply]')", timeout=15000)
    except Exception:
        raise AssertionError(f"import: {pg.evaluate('location.hash')} toast={pg.inner_text('#toast')!r} num={num!r} errors={errors} page={pg.inner_text('#mdPage')[:600]!r}")
    assert "is in the bank line" in pg.inner_text("#mdPage")
    if shots:
        pg.screenshot(path=f"{shots}/books-bank.png")
    pg.click("[data-apply]")
    pg.wait_for_selector("[data-post]", timeout=10000)
    pg.click("[data-post]")
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Every bank line is in the books')", timeout=10000)
    # owed, close, settings
    for tab, want in (("owed", "Customers owe you"), ("close", "checklist"), ("settings", "Chart of accounts"), ("today", "Profit this month")):
        pg.click(f"#sdTabs [data-tab='{tab}']")
        try:
            pg.wait_for_function("(w) => document.querySelector('#mdPage').innerText.includes(w)", arg=want, timeout=10000)
        except Exception:
            raise AssertionError(f"{tab}: errors={errors} page={pg.inner_text('#mdPage')[:500]!r}")
        if shots:
            pg.screenshot(path=f"{shots}/books-{tab}.png")
    assert "1,200" in pg.inner_text("#mdPage")                       # the bank figure comes from the books
    pg.click("#sdTabs [data-tab='close']")
    pg.wait_for_selector("[data-export='xero']")
    with pg.expect_download() as dl:
        pg.click("[data-export='xero']")
    assert dl.value.suggested_filename.endswith("-xero.csv")
    for scheme, width in (("dark", 1440), ("light", 390)):
        c2 = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        c2.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        p2 = c2.new_page()
        p2.on("pageerror", lambda e: errors.append(str(e)))
        p2.goto(base + "/console/books#/bank")
        p2.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Reconciliation')", timeout=15000)
        assert p2.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        c2.close()
    ctx.close()
    assert not errors, errors
