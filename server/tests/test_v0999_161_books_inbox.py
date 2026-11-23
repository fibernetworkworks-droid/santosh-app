"""v0.999.161 BOOKS INBOX: invoices and bills come into the books by themselves - her mail, Hoola's own address, her other programs
(Composio and her books address), her website shop - are read (one AI call), checked in code against the document's own text, and
posted when every check passed (through her approval rules); anything doubtful waits in the Inbox with the reason."""
from __future__ import annotations

import asyncio
from datetime import date

import pytest

T = "default"
TODAY = date.today().isoformat()
BILL = f"""Acme Paper Supplies Ltd
TAX INVOICE
Invoice No: AP-7781
Date: {TODAY}
Bill to: Lumen Studio
A4 paper 10 x 25.00 = 250.00
Net 250.00
VAT 20% 50.00
Total due 300.00
"""
AI = {"is_invoice": True, "doc_type": "invoice", "seller": {"name": "Acme Paper Supplies Ltd", "tax_id": ""},
      "buyer": {"name": "Lumen Studio", "tax_id": ""}, "number": "AP-7781", "issue": TODAY, "due": "", "currency": "GBP",
      "lines": [{"description": "A4 paper", "qty": 10, "price": 25, "tax_pct": 20}], "net": 250, "tax": 50, "total": 300}


@pytest.fixture
def F(env, monkeypatch):
    from app import bookschat as BC
    BC._OF.clear()
    BC._BLOCK.clear()
    from app.fin.desks import books_feed
    calls = {"n": 0, "answer": dict(AI)}

    async def fake(text):
        calls["n"] += 1
        return dict(calls["answer"])
    monkeypatch.setattr(books_feed, "_ai_json", fake)
    books_feed.calls = calls
    books_feed._last.clear()
    return books_feed


def _setup(name="Lumen Studio", cc="GB", cur="GBP"):
    from app.fin import profile as PR
    pv = PR.preview({"size": "business", "countries": [cc], "currency": cur, "name": name, "wants": ["books"]})
    return PR.apply(T, pv["answers"], pv["hash"])["id"]


def run(c):
    return asyncio.run(c)


def test_a_bill_is_read_checked_and_posted_by_itself(F):
    from app.fin.desks import books as BK
    ws = _setup()
    F.set_settings(T, ws, {"on": True})
    r = run(F.ingest(T, ws, "email", "m1#1", "acme.txt", BILL.encode(), sender="billing@acme.example", subject="Your invoice"))
    assert r["status"] == "posted" and r["kind"] == "purchase" and r["party"] == "Acme Paper Supplies Ltd" and r["total"] == 300
    d = [x for x in BK.docs(T, ws, "purchase") if x["id"] == r["doc_id"]][0]
    assert d["status"] == "open" and d["number"] == "AP-7781" and d["total"] == 300 and d["source"] == "email"
    assert BK.balances(T, ws)["6000"] == 25000                 # the expense is in the books
    # the same file again (another mail), and the same bill in another file: never twice
    assert run(F.ingest(T, ws, "email", "m2#1", "copy.txt", BILL.encode()))["skipped"] == "same file"
    assert run(F.ingest(T, ws, "email", "m1#1", "x.txt", b"other"))["skipped"] == "same source"
    dup = run(F.ingest(T, ws, "hoola_mail", "h1#0", "acme2.txt", (BILL + "\nThank you").encode()))
    assert dup["status"] == "duplicate" and dup["doc_id"] == r["doc_id"]
    assert len(BK.docs(T, ws, "purchase")) == 1
    F.calls["answer"] = {**AI, "total": 330, "tax": 80}
    changed = run(F.ingest(T, ws, "email", "m3#1", "acme3.txt", BILL.replace("300.00", "330.00").encode()))
    assert changed["status"] == "failed" and "already in your books for 300" in changed["note"]   # never booked twice
    assert len(BK.docs(T, ws, "purchase")) == 1
    name, data = F.file_of(T, r["id"])
    assert data == BILL.encode()


def test_anything_doubtful_waits_with_the_reason(F):
    from app.fin.desks import books as BK
    ws = _setup()
    F.set_settings(T, ws, {"on": True})
    F.calls["answer"] = {**AI, "total": 3000, "net": 2500, "tax": 500, "lines": [{"description": "A4", "qty": 100, "price": 25, "tax_pct": 20}]}
    r = run(F.ingest(T, ws, "email", "m1#1", "acme.txt", BILL.encode()))
    assert r["status"] == "draft" and "not printed in the document" in r["note"]            # the AI's total is not on the bill
    assert [d["status"] for d in BK.docs(T, ws, "purchase")] == ["draft"]
    F.calls["answer"] = {**AI, "number": "ZZ-1"}
    r2 = run(F.ingest(T, ws, "email", "m2#1", "b.txt", BILL.replace("AP-7781", "AP-7782").encode()))
    assert r2["status"] == "draft" and "ZZ-1" in r2["note"]
    # not an invoice at all: no AI spent
    n = F.calls["n"]
    r3 = run(F.ingest(T, ws, "email", "m3#1", "news.txt", b"Our autumn newsletter. Lots of news about our team and the weather this month."))
    assert r3["status"] == "not_invoice" and F.calls["n"] == n
    F.calls["answer"] = {**AI, "is_invoice": False}
    assert run(F.ingest(T, ws, "email", "m4#1", "q.txt", b"Invoice reminder: please see the attached statement for your account."))["status"] == "not_invoice"
    # she posts the doubtful one herself, or sets it aside (its draft goes; that file is never read again)
    out = F.post(T, ws, r2["id"], "owner")
    assert out["status"] == "posted"
    dropped = F.drop(T, ws, r["id"], "owner")
    assert dropped["status"] == "dropped"
    assert all(d["status"] != "draft" for d in BK.docs(T, ws, "purchase"))
    with pytest.raises(F.FeedError):
        F.drop(T, ws, r2["id"], "owner")                   # already in the books


def test_sales_are_told_from_bills_by_her_tax_number_and_auto_post_off_waits(F):
    from app.fin.desks import books as BK
    ws = _setup()
    F.set_settings(T, ws, {"on": True, "auto_post": False, "tax_ids": ["GB123456789"]})
    F.calls["answer"] = {**AI, "seller": {"name": "Some trading name", "tax_id": "GB 123456789"}, "buyer": {"name": "Northwind Ltd", "tax_id": ""}}
    r = run(F.ingest(T, ws, "software", "xero:LIST:1", "", None, BILL + "GB123456789"))
    assert r["kind"] == "sales" and r["party"] == "Northwind Ltd" and r["status"] == "draft"
    assert BK.docs(T, ws, "sales")[0]["status"] == "draft"


def test_approval_rules_still_apply(F):
    from app.fin.desks import books_ent as E
    from app.db import User, session
    ws = _setup()
    with session() as s:
        s.add(User(id="usr_ann", email="ann@example.com", name="Ann"))
        s.commit()
    E.team_add(T, ws, "ann@example.com", "approver", "Ann", "owner")
    E.set_controls(T, ws, {"on": True, "limit": 100}, "owner")
    F.set_settings(T, ws, {"on": True})
    r = run(F.ingest(T, ws, "email", "m1#1", "acme.txt", BILL.encode()))
    assert r["status"] == "waiting"
    req = E.requests(T, ws)[0]
    assert req["maker_id"] == "hoola-auto"                      # the owner may approve what Hoola posted by itself
    from app import bookschat as BC
    assert BC.do(T, "approve", {"workspace": ws, "request": req["id"]})["status"] == "done"


def test_no_ai_reads_by_rules_and_never_posts_alone(F, monkeypatch):
    async def none(text):
        raise F.FeedError("No AI model is set up on this server.")
    monkeypatch.setattr(F, "_ai_json", none)
    ws = _setup()
    F.set_settings(T, ws, {"on": True})
    r = run(F.ingest(T, ws, "email", "m1#1", "acme.txt", BILL.encode()))
    assert r["reader"] == "rules" and r["status"] == "draft" and r["total"] == 300


def test_her_mail_is_read_by_itself(F, monkeypatch):
    from app.mailbox import service as MS
    ws = _setup()
    F.set_settings(T, ws, {"on": True})
    mails = [{"id": "gm~1", "account": "me@lumen.example", "subject": "Invoice AP-7781", "snippet": "", "has_attachments": True},
             {"id": "gm~2", "account": "me@lumen.example", "subject": "Lunch on Friday?", "snippet": "see you", "has_attachments": False}]
    monkeypatch.setattr(MS, "check", lambda *a, **k: {"emails": mails})
    monkeypatch.setattr(MS, "read", lambda t, ref, *a, **k: {"from_email": "billing@acme.example", "subject": "Invoice AP-7781",
                                                            "attachments": [{"id": "1", "name": "AP-7781.txt"}, {"id": "2", "name": "logo.gif"}]})
    monkeypatch.setattr(MS, "attachment", lambda t, ref, aid: ("AP-7781.txt", "text/plain", BILL.encode()))
    assert run(F.tick()) == 1
    items = F.listing(T, ws)["items"]
    assert [i["status"] for i in items] == ["posted"] and items[0]["sender"] == "billing@acme.example"
    F._last.clear()
    assert run(F.tick()) == 0                                   # read once
    from app import bookschat as BC
    n = BC.numbers(T, ws)
    assert n.get("inbox_posted") == 1 and n.get("inbox_on") is True


def test_hoola_address_shop_and_other_systems(F):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.employee import hire
    from app.fin.desks import books as BK
    hire.hire(T, "books_accounts", trust="seekh")
    ws = _setup()
    F.set_settings(T, ws, {"on": True})
    assert run(F.from_hoola_mail(T, "a@b.example", "Fwd: bill", "", [("acme.txt", BILL.encode())], "am1")) == 1
    assert F.listing(T, ws)["items"][0]["source"] == "hoola_mail"
    c = TestClient(app)
    assert c.post("/api/books/in", json={"documents": []}).status_code == 401
    key = c.post("/api/books/do/inbox_key", json={"workspace": ws}).json()["key"]
    h = {"Authorization": "Bearer " + key}
    out = c.post("/api/books/in", headers=h, json={"from": "My ERP", "documents": [
        {"id": "S-1", "kind": "sales", "party": "Northwind Ltd", "number": "INV-500", "issue": TODAY, "currency": "GBP",
         "lines": [{"description": "Design", "qty": 1, "price": 1000, "tax_pct": 20}], "net": 1000, "tax": 200, "total": 1200}]}).json()
    assert out["items"][0]["status"] == "posted" and out["items"][0]["kind"] == "sales"
    s = [d for d in BK.docs(T, ws, "sales") if d["number"] == "INV-500"]
    assert s and s[0]["total"] == 1200 and s[0]["status"] == "open"
    assert c.post("/api/books/in", headers=h, json={"documents": [{"id": "S-1", "kind": "sales", "party": "X", "total": 5}]}).json()["items"][0]["skipped"]
    c.post("/api/books/do/inbox_key_stop", json={"workspace": ws})
    assert c.post("/api/books/in", headers=h, json={"text": "x"}).status_code == 401
    d = c.post("/api/books/do/inbox", json={"workspace": ws}).json()
    assert d["counts"]["posted"] == 2 and d["settings"]["on"] is True and "hook_hash" not in d["settings"]
    item = [i for i in d["items"] if i["source"] == "hoola_mail"][0]
    assert c.get(f"/api/books/inbox/{item['id']}/file?workspace={ws}").content == BILL.encode()


def test_shop_orders_become_sales_invoices(F):
    import json
    from app.db import session
    from app.fin.desks import books as BK
    from app.site.shop import SiteShopOrder, _ShopTables  # noqa: F401
    from app.site import shop as SH
    ws = _setup(cur="INR", cc="IN")
    F.set_settings(T, ws, {"on": True, "mail": False, "shop": True})
    try:
        SH._tables() if hasattr(SH, "_tables") else None
    except Exception:
        pass
    from app import db as D
    SiteShopOrder.__table__.create(D._engine, checkfirst=True)
    with session() as s:
        s.add(SiteShopOrder(site_id="s1", tenant_id=T, number="W-101", name="Priya", items=json.dumps([{"title": "Mug", "qty": 2, "amount": 50000}]),
                            subtotal=50000, total=50000, status="confirmed"))
        s.add(SiteShopOrder(site_id="s1", tenant_id=T, number="W-102", name="Ravi", items="[]", total=100, status="new"))
        s.commit()
    assert run(F.scan_now(T, ws)) == 1
    s = BK.docs(T, ws, "sales")
    assert len(s) == 1 and s[0]["party"] == "Priya" and s[0]["total"] == 500 and s[0]["number"] == "W-101"
    assert run(F.scan_now(T, ws)) == 0


def test_desk_has_the_inbox(F):
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "app/static/console/booksdesk.js").read_text()
    for k in ("['inbox', 'Inbox']", "pInbox", "data-inscan", "data-inpost", "data-indrop", "data-inkey", "inbox_needs"):
        assert k in js, k
    from app.fin.desks import books_ent as E
    assert E.allowed("viewer", "inbox") and not E.allowed("viewer", "inbox_post") and not E.allowed("accountant", "inbox_key")
    assert E.allowed("accountant", "inbox_post")


from tests.test_v0999_158_books_desk import bk, bk_server   # noqa: E402,F401  the real-server + Chromium fixture


def test_inbox_in_a_real_browser(bk_server, monkeypatch):
    import os
    from app.fin.desks import books_feed as Fd
    base, browser, key = bk_server
    shots = os.environ.get("HOOLA_SHOTS")

    async def fake(text):
        return {**AI, "number": "AP-9", "total": 999} if "AP-9" in text else dict(AI)
    monkeypatch.setattr(Fd, "_ai_json", fake)
    ws = _setup()
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}'); localStorage.setItem('hoola.books.ws', '{ws}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/books#/inbox")
    pg.wait_for_selector("[data-inon='1']", timeout=20000)
    if shots:
        pg.screenshot(path=f"{shots}/books-inbox-off.png", full_page=True)
    pg.click("[data-inon='1']")
    pg.wait_for_selector("[data-insave]", timeout=10000)
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(1) as ex:      # the browser fixture owns this thread's event loop
        ex.submit(asyncio.run, Fd.ingest(T, ws, "email", "m1#1", "acme.txt", BILL.encode(), sender="billing@acme.example", subject="Invoice")).result()
        ex.submit(asyncio.run, Fd.ingest(T, ws, "email", "m2#1", "odd.txt", BILL.replace("AP-7781", "AP-9").encode(), sender="x@y.example",
                                         subject="Bill")).result()
    pg.click("#sdRefresh")
    try:
        pg.wait_for_selector("[data-inpost]", timeout=10000)
    except Exception:
        raise AssertionError(f"{pg.inner_text('#mdPage')[:1200]!r} {Fd.listing(T, ws)['counts']} {errors}")
    txt = pg.inner_text("#mdPage")
    assert "Posted" in txt and "Needs your look" in txt and "not printed in the document" in txt, txt[:900]
    assert pg.inner_text("#sdTabs").count("Inbox") == 1
    if shots:
        pg.screenshot(path=f"{shots}/books-inbox.png", full_page=True)
    pg.click("[data-inpost]")
    pg.wait_for_function("() => document.querySelector('#toast').innerText.includes('Posted')", timeout=10000)
    pg.wait_for_function("() => !document.querySelector('[data-inpost]')", timeout=10000)
    pg.goto(base + "/console/books#/today")
    pg.wait_for_selector("#mdPage .bk-4", timeout=10000)
    assert not errors, errors
    ctx.close()
