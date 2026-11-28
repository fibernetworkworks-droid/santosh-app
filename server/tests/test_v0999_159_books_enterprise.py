"""v0.999.159 BOOKS ENTERPRISE: team roles on one business's books, a second person approving postings (never the maker; two
above her limit), cost centres with profit by cost centre, group accounts in one currency with her rates and intercompany
eliminated, and bank matching that stays fast on a big business (plus the 5,000-line cap the engine silently had)."""
from __future__ import annotations

import time
from datetime import date

import pytest

T = "default"


@pytest.fixture
def E(env):
    from app import bookschat as BC
    BC._OF.clear()
    BC._BLOCK.clear()
    from app.fin.desks import books_ent
    return books_ent


def _setup(tenant=T, name="Lumen Studio", cc="GB", cur="GBP", size="business"):
    from app.fin import profile as PR
    pv = PR.preview({"size": size, "countries": [cc], "currency": cur, "name": name, "wants": ["books"]})
    return PR.apply(tenant, pv["answers"], pv["hash"])["id"]


def _user(uid, email, name):
    from app.db import User, session
    with session() as s:
        s.add(User(id=uid, email=email, name=name))
        s.commit()


def _do(caller, part, **a):
    from app import bookschat as BC
    return BC.do(caller, part, a)


def test_controls_off_posts_at_once_and_on_needs_an_approver(E):
    from app.fin.desks import books as BK
    ws = _setup()
    j = BK.run(T, "journal", {"workspace": ws, "lines": [{"code": "6000", "debit": 50}, {"code": "1000", "credit": 50}]})
    assert j["journal"]                                         # controls off: unchanged behaviour
    with pytest.raises(E.EntError):
        E.set_controls(T, ws, {"on": True}, "owner")              # nobody to approve yet
    _user("usr_ann", "ann@example.com", "Ann")
    E.team_add(T, ws, "ANN@example.com", "approver", "Ann", "owner")
    assert E.set_controls(T, ws, {"on": True, "limit": 100, "dual": 1000}, "owner")["on"] is True
    small = BK.run(T, "journal", {"workspace": ws, "lines": [{"code": "6000", "debit": 80}, {"code": "1000", "credit": 80}]})
    assert small.get("journal")                                 # under her limit: posted
    big = BK.run(T, "journal", {"workspace": ws, "_approved_by": "me", "lines": [{"code": "6000", "debit": 500}, {"code": "1000", "credit": 500}]})
    assert big["queued"] and big["needs"] == 1                  # an argument can never claim an approval
    again = BK.run(T, "journal", {"workspace": ws, "lines": [{"code": "6000", "debit": 500}, {"code": "1000", "credit": 500}]})
    assert again["request"] == big["request"]                   # the same posting twice = one request
    before = BK.balances(T, ws)
    with pytest.raises(E.EntError):
        _do(T, "approve", workspace=ws, request=big["request"])  # the owner made it (through the tool): not her to approve
    out = _do("usr_ann", "approve", workspace=ws, request=big["request"])
    assert out["status"] == "done" and BK.balances(T, ws)["6000"] == before["6000"] + 50000
    with pytest.raises(E.EntError):
        _do("usr_ann", "approve", workspace=ws, request=big["request"])   # runs once
    huge = BK.run(T, "journal", {"workspace": ws, "lines": [{"code": "6000", "debit": 5000}, {"code": "1000", "credit": 5000}]})
    assert huge["needs"] == 2
    assert _do("usr_ann", "approve", workspace=ws, request=huge["request"])["status"] == "pending"
    with pytest.raises(E.EntError):
        _do("usr_ann", "approve", workspace=ws, request=huge["request"])  # a second approver must be a different person
    _user("usr_raj", "raj@example.com", "Raj")
    E.team_add(T, ws, "raj@example.com", "admin", "Raj", "owner")
    assert _do("usr_raj", "approve", workspace=ws, request=huge["request"])["status"] == "done"
    dep = BK.run(T, "depreciation", {"workspace": ws, "period": date.today().strftime("%Y-%m")})
    assert dep["queued"]                                         # no amount known before it runs: always approved
    assert _do("usr_raj", "reject", workspace=ws, request=dep["request"], reason="Not this month")["status"] == "rejected"
    assert E.requests(T, ws) == []


def test_roles_and_who_may_open_the_books(E):
    ws = _setup()
    _user("usr_v", "v@example.com", "Vee")
    _user("usr_acc", "acc@example.com", "Asha")
    _user("usr_x", "x@example.com", "Stranger")
    E.team_add(T, ws, "v@example.com", "viewer", "Vee", "owner")
    E.team_add(T, ws, "acc@example.com", "accountant", "Asha", "owner")
    with pytest.raises(E.EntError):
        E.access("usr_x", ws)                                    # not on these books
    assert _do("usr_v", "documents", workspace=ws)["documents"] == []
    with pytest.raises(E.EntError):
        _do("usr_v", "invoice", workspace=ws, party="A", lines=[{"description": "x", "price": 10}])
    with pytest.raises(E.EntError):
        _do("usr_v", "export", workspace=ws, format="csv")       # a viewer reads, never downloads
    inv = _do("usr_acc", "invoice", workspace=ws, party="Northwind", lines=[{"description": "x", "price": 10}], issue_now=True)
    assert inv["number"]                                         # controls off: an accountant posts directly
    with pytest.raises(E.EntError):
        _do("usr_acc", "approve", workspace=ws, request="nope")
    with pytest.raises(E.EntError):
        _do("usr_acc", "team_add", workspace=ws, email="z@example.com", role="viewer")
    with pytest.raises(E.EntError):
        _do("usr_acc", "close_lock", workspace=ws, period="2026-01", hash="x")
    from app import bookschat as BC
    d = BC.summary("usr_acc")                                    # she never hired anything: the shared books still open
    assert d["hired"] and d["role"] == "accountant" and d["workspace"]["id"] == ws and "approve" not in d["can"]
    assert [b["role"] for b in BC.businesses("usr_acc")] == ["accountant"]
    E.team_remove(T, ws, [m for m in E.team(T, ws) if m["email"] == "acc@example.com"][0]["id"], "owner")
    with pytest.raises(E.EntError):
        E.access("usr_acc", ws)


def test_controls_on_invoice_issue_waits_and_the_maker_is_the_person(E):
    from app.fin.desks import books as BK
    ws = _setup()
    for uid, em, r in (("usr_acc", "acc@example.com", "accountant"), ("usr_ap", "ap@example.com", "approver")):
        _user(uid, em, uid)
        E.team_add(T, ws, em, r, uid, "owner")
    E.set_controls(T, ws, {"on": True, "limit": 0}, "owner")
    inv = _do("usr_acc", "invoice", workspace=ws, party="Northwind", lines=[{"description": "x", "price": 300}], issue_now=True)
    assert inv["status"] == "draft" and inv["approval"]["queued"]
    req = E.requests(T, ws)[0]
    assert req["maker_id"] == "usr_acc" and "Northwind" in req["what"]
    with pytest.raises(E.EntError):
        _do("usr_acc", "approve", workspace=ws, request=req["id"])   # cannot approve her own (and has no approve role)
    assert _do(T, "approve", workspace=ws, request=req["id"])["status"] == "done"   # the owner may approve the accountant's
    d = BK.docs(T, ws)[0]
    assert d["status"] == "open" and d["number"]
    with pytest.raises(E.EntError):
        E.team_remove(T, ws, "nope", "owner")
    ap = [m for m in E.team(T, ws) if m["role"] == "approver"][0]["id"]
    E.team_remove(T, ws, ap, "owner")
    assert E.controls(T, ws)["on"] is False                        # nobody left to approve: the switch turns itself off


def test_cost_centres(E):
    from app.fin.desks import books as BK
    ws = _setup()
    E.set_controls(T, ws, {"cost_centres": "Sales, Studio, Sales"}, "owner")
    assert E.controls(T, ws)["cost_centres"] == ["Sales", "Studio"]
    with pytest.raises(BK.BooksError):
        BK.run(T, "invoice", {"workspace": ws, "party": "A", "cost_centre": "Nowhere", "lines": [{"description": "x", "price": 10}]})
    BK.run(T, "invoice", {"workspace": ws, "party": "A", "cost_centre": "Sales", "issue_now": True, "lines": [{"description": "x", "price": 1000}]})
    BK.run(T, "bill", {"workspace": ws, "party": "B", "cost_centre": "Studio", "issue_now": True, "lines": [{"description": "y", "price": 300}]})
    BK.run(T, "journal", {"workspace": ws, "lines": [{"code": "6000", "debit": 40, "cost_centre": "Sales"}, {"code": "1000", "credit": 40}]})
    r = E.by_cost_centre(T, ws, "0000-01-01", "9999-12-31")
    rows = {x["cost_centre"]: x for x in r["rows"]}
    assert rows["Sales"]["income"] == 1000 and rows["Sales"]["expenses"] == 40 and rows["Studio"]["expenses"] == 300
    assert r["total_profit"] == 660


def test_group_accounts_with_her_rates_and_intercompany(E):
    from app.fin.desks import books as BK
    uk = _setup(name="Lumen UK")
    de = _setup(name="Lumen GmbH", cc="DE", cur="EUR")
    t = date.today().isoformat()
    BK.run(T, "invoice", {"workspace": uk, "party": "Outside Ltd", "issue_now": True, "lines": [{"description": "x", "price": 1000}]})
    BK.run(T, "invoice", {"workspace": uk, "party": "Lumen GmbH", "intercompany": de, "issue_now": True,
                          "lines": [{"description": "Design for the group", "price": 200}]})
    BK.run(T, "bill", {"workspace": de, "party": "Lumen UK", "intercompany": uk, "issue_now": True, "currency": "EUR",
                       "lines": [{"description": "Design", "price": 230}]})
    with pytest.raises(BK.BooksError):
        BK.run(T, "invoice", {"workspace": uk, "party": "Me", "intercompany": uk, "lines": [{"description": "x", "price": 1}]})
    with pytest.raises(E.EntError):
        E.consolidate(T, [uk, de], "GBP", {}, "0000-01-01", t)     # a currency with no rate is refused, never guessed
    g = E.consolidate(T, [uk, de], "GBP", {"EUR": {"average": 0.8695652, "closing": 0.8695652}}, "0000-01-01", t)
    assert g["profit_and_loss"]["income"] == 1000.0               # the 200 sold inside the group is taken out
    assert g["profit_and_loss"]["expenses"] == pytest.approx(0, abs=0.01)
    assert g["eliminations"] and not g["mismatches"]
    g2 = E.consolidate(T, [uk, de], "GBP", {"EUR": {"average": 0.8, "closing": 0.8}}, "0000-01-01", t)
    assert g2["mismatches"]                                       # 230 EUR at 0.8 = 184, not 200: named, never hidden
    with pytest.raises(E.EntError):
        E.consolidate("someone-else", [uk, de], "GBP", {"EUR": {"average": 1, "closing": 1}}, "0000-01-01", t)


def test_matching_is_fast_on_a_big_business_and_sees_every_line(E):
    from app.db import session
    from app.fin import models as M
    from app.fin.desks import books as BK
    ws = _setup()
    BK.ensure_coa(T, ws)
    n_docs, n_lines = 3000, 12000
    with session() as s:
        for i in range(n_docs):
            s.add(M.FinInvoice(tenant_id=T, workspace_id=ws, kind="sales", number=f"INV-2026-{i + 1:04d}", party=f"Customer {i}",
                               issue="2026-01-01", due="2026-02-01", currency="GBP", net_minor=10000 + i, total_minor=10000 + i,
                               status="open"))
        for i in range(n_lines):
            nar = f"PAYMENT INV-2026-{(i % n_docs) + 1:04d}" if i < n_docs else f"CARD SHOP {i}"
            s.add(M.FinTxn(tenant_id=T, workspace_id=ws, account_id="acc", day=f"2025-{(i % 12) + 1:02d}-15",
                           amount_minor=(10000 + i) if i < n_docs else -(500 + i), currency="GBP", narration=nar, dedup=f"h{i}"))
        s.commit()
    t0 = time.time()
    m = BK.propose_matches(T, ws, limit=n_lines)
    took = time.time() - t0
    assert m["total"] == n_lines                                   # every line, not the newest 5,000
    sure = [x for x in m["lines"] if x.get("sure")]
    assert len(sure) == n_docs
    assert took < 20, f"matching {n_lines} lines took {took:.1f} s"
    assert len(BK.propose_matches(T, ws)["lines"]) == 500 and BK.propose_matches(T, ws)["more"] == n_lines - 500
    old = [x for x in m["lines"] if x["day"].startswith("2025-01")][0]
    assert BK._bank_line(T, ws, old["txn"])                        # an old line can still be confirmed


def test_desk_routes_and_files(E):
    from pathlib import Path
    from fastapi.testclient import TestClient
    from app.main import app
    from app.employee import hire
    hire.hire(T, "books_accounts", trust="seekh")
    ws = _setup()
    c = TestClient(app)
    d = c.get(f"/api/books/desk?workspace={ws}").json()
    assert d["role"] == "owner" and "approve" in d["can"] and d["controls"]["on"] is False and d["pending"] == 0
    assert c.post("/api/books/do/team_add", json={"workspace": ws, "email": "bad", "role": "viewer"}).status_code == 400
    assert c.post("/api/books/do/team_add", json={"workspace": ws, "email": "p@example.com", "role": "approver"}).status_code == 200
    assert c.post("/api/books/do/controls", json={"workspace": ws, "on": True, "limit": 0}).json()["on"] is True
    r = c.post("/api/books/do/journal", json={"workspace": ws, "lines": [{"code": "6000", "debit": 5}, {"code": "1000", "credit": 5}]}).json()
    assert r["queued"]
    assert c.get(f"/api/books/desk?workspace={ws}").json()["pending"] == 1
    assert c.post("/api/books/do/requests", json={"workspace": ws}).json()["requests"][0]["action"] == "journal"
    assert c.post("/api/books/do/nope", json={"workspace": "other"}).status_code == 400
    js = (Path(__file__).resolve().parents[1] / "app/static/console/booksdesk.js").read_text()
    for k in ("/api/books/do/", "pApprovals", "data-approve", "data-form=\"controls\"", "data-form=\"team\"", "data-form=\"group\"", "ccTable"):
        assert k in js, k


from tests.test_v0999_158_books_desk import bk, bk_server   # noqa: E402,F401  the real-server + Chromium fixture


def test_enterprise_desk_in_a_real_browser(bk_server):
    import os
    from app.fin.desks import books_ent as E
    base, browser, key = bk_server
    shots = os.environ.get("HOOLA_SHOTS")
    ws = _setup()
    _setup(name="Lumen GmbH", cc="DE", cur="EUR")
    _user("usr_acc", "acc@example.com", "Asha")
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}'); localStorage.setItem('hoola.books.ws', '{ws}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept("Wrong amount"))
    # the team and the controls, from Settings
    pg.goto(base + "/console/books#/settings")
    pg.wait_for_selector("form[data-form=team]", timeout=20000)
    pg.fill("#bkTE", "acc@example.com")
    pg.fill("#bkTN", "Asha")
    pg.select_option("#bkTR", "accountant")
    pg.click("form[data-form=team] button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('acc@example.com')", timeout=10000)
    pg.fill("#bkTE", "ann@example.com")
    pg.select_option("#bkTR", "approver")
    pg.click("form[data-form=team] button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('ann@example.com')", timeout=10000)
    pg.check("form[data-form=controls] input[name=on]")
    pg.fill("#bkLim", "0")
    pg.fill("#bkCCs", "Sales, Studio")
    pg.click("form[data-form=controls] button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#sdTabs').innerText.includes('Approvals')", timeout=10000)
    if shots:
        pg.screenshot(path=f"{shots}/books-team.png", full_page=True)
    # the owner's invoice waits; she cannot approve her own
    pg.goto(base + "/console/books#/docs/new-sales")
    pg.wait_for_selector("#bkCC")
    pg.fill("#bkParty", "Northwind Ltd")
    pg.fill("#bkD0", "Retainer")
    pg.fill("#bkP0", "1000")
    pg.select_option("#bkCC", "Sales")
    pg.click("form[data-form=doc] button[value=issue]")
    try:
        pg.wait_for_function("() => document.querySelector('#toast').innerText.includes('waits')", timeout=10000)
    except Exception:
        raise AssertionError(f"issue: hash={pg.evaluate('location.hash')} toast={pg.inner_text('#toast')!r} errors={errors}")
    pg.wait_for_function("() => location.hash === '#/docs'", timeout=10000)
    E.hold(T, ws, "journal", {"workspace": ws, "lines": [{"code": "6000", "debit": 70}, {"code": "1000", "credit": 70}]}, "Asha <usr_acc>")
    pg.goto(base + "/console/books#/approvals")
    try:
        pg.wait_for_function("() => document.querySelectorAll('[data-approve]').length === 2", timeout=10000)
    except Exception:
        raise AssertionError(f"approvals: {pg.evaluate('location.hash')} {pg.inner_text('#mdPage')[:900]!r} {E.requests(T, ws)!r}")
    if shots:
        pg.screenshot(path=f"{shots}/books-approvals.png")
    rows = pg.evaluate("[...document.querySelectorAll('#mdPage tr')].map(t => t.innerText.slice(0, 80))")
    assert any("Invoice Northwind" in r for r in rows), rows
    pg.locator("tr", has_text="Invoice Northwind").locator("[data-approve]").click(timeout=5000)
    try:
        pg.wait_for_function("() => document.querySelector('#toast').innerText.includes('another person')", timeout=10000)
    except Exception:
        raise AssertionError(f"toast={pg.inner_text('#toast')!r} page={pg.inner_text('#mdPage')[:700]!r} errors={errors}")
    pg.locator("tr", has_text="Journal").locator("[data-approve]").click()
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Posted')", timeout=10000)
    pg.locator("tr", has_text="Invoice Northwind").locator("[data-reject]").click()
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Wrong amount')", timeout=10000)
    # profit by cost centre + group accounts on Reports
    pg.click("#sdTabs [data-tab='close']")
    pg.wait_for_selector("form[data-form=group]", timeout=10000)
    pg.select_option("#bkPer", date.today().strftime("%Y-%m"))
    pg.wait_for_function("() => document.querySelector('#bkGA_EUR')", timeout=10000)
    pg.fill("#bkGA_EUR", "0.86")
    pg.fill("#bkGL_EUR", "0.86")
    pg.click("form[data-form=group] button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Translation and intercompany difference')", timeout=10000)
    assert "Profit by cost centre" in pg.inner_text("#mdPage")
    if shots:
        pg.screenshot(path=f"{shots}/books-group.png", full_page=True)
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    ctx.close()
    assert not errors, errors
