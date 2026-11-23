"""v0.999.167 BANK CONNECT: a business's bank accounts come into Books & Accounts the way that works in her country -
a bank connection through a licensed open-banking partner (she signs in at her own bank, read-only), bank files
(MT940 / CAMT.053 / OFX / QIF by mail or the books address), her bank's statement mail, or an upload - and every route
lands bank lines in the same place for matching. No bank password ever; no live partner call (fake transport)."""
from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta

import httpx
import pytest

T = "default"
TODAY = date.today().isoformat()
MT940 = (":20:STMT1\n:25:GB29NWBK60161331926819\n:28C:1/1\n:60F:C" + date.today().strftime("%y%m%d") + "GBP1000,00\n"
         ":61:" + date.today().strftime("%y%m%d") + "C250,00NTRFNONREF//X\n:86:ACME LTD INV AP-7781\n"
         ":61:" + date.today().strftime("%y%m%d") + "D40,00NTRFNONREF//Y\n:86:CARD COFFEE\n:62F:C" + date.today().strftime("%y%m%d") + "GBP1210,00\n-")
CSV = f"Date,Narration,Debit,Credit\n{date.today().strftime('%d/%m/%Y')},UPI RAJ TRADERS,,1500.00\n{date.today().strftime('%d/%m/%Y')},ATM CASH,200.00,\n"


@pytest.fixture
def B(env, monkeypatch):
    from app import bookschat as BC
    BC._OF.clear()
    BC._BLOCK.clear()
    from app.config import get_settings
    st = get_settings()
    for k, v in {"public_base_url": "https://hoola.example", "gocardless_secret_id": "id", "gocardless_secret_key": "key",
                 "plaid_client_id": "pc", "plaid_secret": "ps", "setu_aa_client_id": "sc", "setu_aa_client_secret": "ss",
                 "setu_aa_product_instance": "pi", "open_banking_ack": "gocardless, plaid, setu_aa", "secret_key": st.secret_key or "test-key"}.items():
        monkeypatch.setattr(st, k, v)
    from app.fin.desks import books_bank
    from app.fin.sources import openbanking as OB
    OB.GoCardless._tok = (0.0, "")
    books_bank._last.clear()
    return books_bank


def _setup(name="Lumen Studio", cc="GB", cur="GBP"):
    from app.fin import profile as PR
    pv = PR.preview({"size": "business", "countries": [cc], "currency": cur, "name": name, "wants": ["books"]})
    return PR.apply(T, pv["answers"], pv["hash"])["id"]


def _fake(monkeypatch, handler):
    from app.fin.sources import openbanking as OB
    calls = []

    def h(method, url, **kw):
        calls.append((method, url, kw))
        code, body = handler(method, url, kw)
        return httpx.Response(code, json=body, request=httpx.Request(method, url))
    monkeypatch.setattr(OB, "_http", h)
    return calls


def test_routes_follow_her_country(B, monkeypatch):
    from app.config import get_settings
    from app.fin.sources import openbanking as OB
    assert OB.for_country("IN")["state"] == "ready" and OB.for_country("IN")["needs"] == "mobile"
    assert OB.for_country("DE")["partner"] == "gocardless" and OB.for_country("CA")["partner"] == "plaid"
    assert OB.for_country("AU")["state"] == "later" and "Basiq" in OB.for_country("AU")["why"]
    assert OB.for_country("JP")["state"] == "none" and "upload work everywhere" in OB.for_country("JP")["why"]
    monkeypatch.setattr(get_settings(), "open_banking_ack", "plaid")           # keys set but terms not marked read
    assert OB.for_country("GB")["state"] == "terms"
    monkeypatch.setattr(get_settings(), "gocardless_secret_key", "")
    assert OB.for_country("GB")["state"] == "not_set_up"
    ws = _setup()
    with pytest.raises(B.BankFeedError):
        B.connect(T, ws, "GB", bank="X")                                       # not offered, said plainly
    r = B.routes(T, ws)
    assert r["countries"] == ["GB"] and r["connection"][0]["state"] == "not_set_up" and "CAMT.053" in r["upload"]["formats"]


def test_gocardless_end_to_end(B, monkeypatch):
    from app.fin import spine as SP
    tx = {"booked": [{"transactionId": "t1", "bookingDate": TODAY, "transactionAmount": {"amount": "250.00", "currency": "GBP"},
                      "debtorName": "ACME LTD", "remittanceInformationUnstructured": "INV AP-7781"},
                     {"transactionId": "t2", "bookingDate": TODAY, "transactionAmount": {"amount": "-40.00", "currency": "GBP"},
                      "creditorName": "Coffee"}], "pending": []}

    def h(m, url, kw):
        if url.endswith("/token/new/"):
            assert kw["json"] == {"secret_id": "id", "secret_key": "key"}
            return 200, {"access": "AT", "access_expires": 86400}
        assert kw["headers"]["Authorization"] == "Bearer AT"
        if "/institutions/" in url:
            return 200, [{"id": "MONZO_X", "name": "Monzo"}, {"id": "HSBC_X", "name": "HSBC"}]
        if url.endswith("/agreements/enduser/"):
            assert kw["json"]["access_scope"] == ["balances", "details", "transactions"]
            return 201, {"id": "ag1"}
        if url.endswith("/requisitions/") and m == "POST":
            assert kw["json"]["redirect"].startswith("https://hoola.example/api/books/bank/back?s=") and kw["json"]["agreement"] == "ag1"
            return 201, {"id": "rq1", "link": "https://ob.gocardless.com/psd2/start/rq1"}
        if url.endswith("/requisitions/rq1/") and m == "GET":
            return 200, {"status": "LN", "accounts": ["acc1"]}
        if url.endswith("/accounts/acc1/details/"):
            return 200, {"account": {"iban": "GB29NWBK60161331926819", "currency": "GBP", "name": "Business current"}}
        if url.endswith("/accounts/acc1/transactions/"):
            return 200, {"transactions": tx}
        if m == "DELETE":
            return 200, {}
        raise AssertionError(url)
    calls = _fake(monkeypatch, h)
    ws = _setup()
    assert [b["name"] for b in B.banks(T, ws, "GB", "mon")["banks"]] == ["Monzo"]
    r = B.connect(T, ws, "GB", account="Main current", bank="MONZO_X", actor="Meg")
    assert r["url"].startswith("https://ob.gocardless.com/") and "never sees your bank password" in r["says"]
    state = [c for c in calls if c[1].endswith("/requisitions/")][0][2]["json"]["reference"]
    out = B.back(state)
    assert out["ok"] and out["link"]["added"] == 2 and out["link"]["accounts"][0]["masked"] == "...6819"
    assert B.back(state)["ok"] is False                                          # the key is one-time
    lines = SP.txns(T, ws)
    assert sorted(l["amount"] for l in lines) == ["-40.00", "250.00"] and {l["source"] for l in lines} == {"bank"}
    acct = [a for a in B.overview(T, ws)["accounts"] if a["name"] == "Main current"][0]
    assert acct["sources"] == ["Bank connection"] and acct["txns"] == 2
    assert B.sync_now(T, ws)["added"] == 0                                       # never twice
    from app.fin.desks import books as BK
    assert BK.run(T, "matches", {"workspace": ws}, "Meg")["total"] == 2          # straight into matching
    d = B.disconnect(T, ws, out["link"]["id"], "Meg")
    assert "stay" in d["says"] and any(c[0] == "DELETE" for c in calls) and d["bank"]["links"] == []


def test_plaid_hosted_link_and_sign(B, monkeypatch):
    from app.fin import spine as SP
    seen = {"sync": 0}

    def h(m, url, kw):
        b = kw["json"]
        assert b["client_id"] == "pc" and b["secret"] == "ps" and url.startswith("https://sandbox.plaid.com/")
        if url.endswith("/link/token/create"):
            assert b["hosted_link"]["completion_redirect_uri"].startswith("https://hoola.example/") and b["country_codes"] == ["US"]
            return 200, {"link_token": "lt1", "hosted_link_url": "https://secure.plaid.com/hl/lt1"}
        if url.endswith("/link/token/get"):
            return 200, {"link_sessions": [{"results": {"item_add_results": [{"public_token": "pub1"}]}}]}
        if url.endswith("/item/public_token/exchange"):
            return 200, {"access_token": "access-sandbox-1"}
        if url.endswith("/accounts/get"):
            return 200, {"accounts": [{"account_id": "A1", "name": "Checking", "mask": "0000", "balances": {"iso_currency_code": "USD"}}],
                         "item": {"institution_name": "Chase"}}
        if url.endswith("/transactions/sync"):
            assert b["access_token"] == "access-sandbox-1"
            seen["sync"] += 1
            if b.get("cursor") == "c2":
                return 200, {"added": [], "next_cursor": "c2", "has_more": False}
            if not b.get("cursor"):
                return 200, {"added": [{"account_id": "A1", "transaction_id": "p1", "date": TODAY, "amount": 12.5, "name": "Starbucks",
                                        "iso_currency_code": "USD"}], "next_cursor": "c1", "has_more": True}
            return 200, {"added": [{"account_id": "A1", "transaction_id": "p2", "date": TODAY, "amount": -900, "name": "Client payment",
                                    "iso_currency_code": "USD"}], "next_cursor": "c2", "has_more": False}
        raise AssertionError(url)
    _fake(monkeypatch, h)
    ws = _setup("Lumen US", "US", "USD")
    r = B.connect(T, ws, "US")
    v = B.refresh(T, r["link"])
    assert v["status"] == "active" and v["institution"] == "Chase" and v["added"] == 2
    amounts = sorted(l["amount"] for l in SP.txns(T, ws))
    assert amounts == ["-12.50", "900.00"]                                       # Plaid's + is money out
    assert B.refresh(T, r["link"])["added"] == 0                                 # the cursor carries on
    from app.db import session
    from app.fin.models import FinBankLink
    with session() as s:
        l = s.get(FinBankLink, r["link"])
        assert l.cursor == "c2" and "access-sandbox-1" not in l.token_sealed and l.token_sealed   # sealed, never plain


def test_setu_account_aggregator(B, monkeypatch):
    from app.fin import spine as SP

    def h(m, url, kw):
        assert kw["headers"]["x-client-id"] == "sc" and kw["headers"]["x-product-instance-id"] == "pi"
        if url.endswith("/v2/consents") and m == "POST":
            assert kw["json"]["vua"] == "9876543210"
            return 201, {"id": "cn1", "url": "https://anumati.setu.co/cn1", "status": "PENDING"}
        if url.endswith("/v2/consents/cn1"):
            return 200, {"status": "ACTIVE", "accountsLinked": [{"linkRefNumber": "L1", "maskedAccNumber": "XXXX1234", "fipId": "HDFC", "accType": "CURRENT"}]}
        if url.endswith("/v2/sessions") and m == "POST":
            assert kw["json"]["consentId"] == "cn1"
            return 201, {"id": "ss1", "status": "PENDING"}
        if url.endswith("/v2/sessions/ss1"):
            return 200, {"status": "COMPLETED", "fips": [{"accounts": [{"linkRefNumber": "L1", "data": {"account": {"transactions": {"transaction": [
                {"txnId": "x1", "type": "CREDIT", "amount": "1500.00", "valueDate": TODAY, "narration": "UPI RAJ TRADERS"},
                {"txnId": "x2", "type": "DEBIT", "amount": "200", "valueDate": TODAY, "narration": "ATM"}]}}}}]}]}
        raise AssertionError(url)
    _fake(monkeypatch, h)
    ws = _setup("Raj Kirana", "IN", "INR")
    with pytest.raises(B.BankFeedError):
        B.connect(T, ws, "IN", mobile="123")                                    # her mobile, never a bank password
    r = B.connect(T, ws, "IN", mobile="+91 98765 43210")
    assert r["url"] == "https://anumati.setu.co/cn1"
    v = B.refresh(T, r["link"])
    assert v["status"] == "active" and v["accounts"][0]["masked"] == "...1234" and v["added"] == 2
    assert sorted(l["amount"] for l in SP.txns(T, ws)) == ["-200.00", "1500.00"]


def test_statement_mail_bank_files_and_the_invoice_reader(B, monkeypatch):
    from app.fin import spine as SP
    from app.fin.desks import books_feed as F
    ws = _setup()
    with pytest.raises(B.BankFeedError):
        B.sender_add(T, ws, "not an address", "Main")
    B.sender_add(T, ws, "@hdfcbank.example", "HDFC current", password="DDMMYYYY")
    ov = B.overview(T, ws)
    assert ov["senders"] == [{"match": "@hdfcbank.example", "account": "HDFC current", "password": True}]
    assert "DDMMYYYY" not in json.dumps(B.settings(T, ws))                         # sealed
    got = B.take_file(T, ws, "estatement@hdfcbank.example", "stmt.csv", CSV.encode(), "m1#1")
    assert got["added"] == 2 and got["account"]["name"] == "HDFC current"
    assert B.take_file(T, ws, "estatement@hdfcbank.example", "stmt.csv", CSV.encode(), "m1#1") == {"skipped": "already read"}
    mt = B.take_file(T, ws, "noreply@ledger.example", "today.sta", MT940.encode(), "m2#1")   # a bank file by its own format
    assert mt["added"] == 2 and mt["format"] == "mt940" and mt["account"]["name"] == "Bank account ...6819"
    assert B.take_file(T, ws, "billing@acme.example", "AP-7781.pdf", b"%PDF-1.4 not a statement", "m3#1") is None   # an invoice: not ours
    srcs = {a["name"]: a["sources"] for a in B.overview(T, ws)["accounts"]}
    assert srcs["HDFC current"] == ["Statement mail"] and srcs["Bank account ...6819"] == ["Bank file"]
    # through the mail reader: statements become bank lines even with the invoice inbox off, never invoices
    from app.mailbox import service as MS
    monkeypatch.setattr(F, "_boxes", lambda t: [{"address": "me@lumen.example", "kind": "gmail", "status": "ok"}])
    F.attach_mail(T, ws, "me@lumen.example")
    assert not F.settings(T, ws).get("on")
    mails = [{"id": "gm~9", "account": "me@lumen.example", "subject": "Your statement", "snippet": "", "has_attachments": True}]
    monkeypatch.setattr(MS, "check", lambda *a, **k: {"emails": mails})
    monkeypatch.setattr(MS, "read", lambda t, ref, *a, **k: {"from_email": "alerts@hdfcbank.example", "subject": "Your statement",
                                                            "attachments": [{"id": "1", "name": "Statement_Nov.csv"}]})
    csv2 = CSV.replace("RAJ TRADERS", "MEHTA AND SONS")
    monkeypatch.setattr(MS, "attachment", lambda t, ref, aid: ("Statement_Nov.csv", "text/csv", csv2.encode()))

    async def no_ingest(*a, **k):
        raise AssertionError("a statement never goes to the invoice reader")
    monkeypatch.setattr(F, "ingest", no_ingest)
    F._last.clear()
    asyncio.run(F.tick())
    assert any("MEHTA" in l["narration"] for l in SP.txns(T, ws))


def test_bank_file_address_and_roles(B):
    from fastapi.testclient import TestClient
    from app.fin.desks import books_ent as E
    from app.fin.desks import books_feed as F
    from app.main import app
    ws = _setup()
    key = F.new_api_key(T, ws)["key"]
    c = TestClient(app)
    assert c.post("/api/books/bank-file", json={"text": MT940}).status_code == 401
    r = c.post("/api/books/bank-file", headers={"Authorization": f"Bearer {key}"}, json={"account": "Barclays", "name": "x.sta", "text": MT940})
    assert r.status_code == 200 and r.json()["added"] == 2 and r.json()["account"]["name"] == "Barclays"
    assert c.post("/api/books/bank-file", headers={"Authorization": f"Bearer {key}"}, json={"text": "hello"}).status_code == 400
    page = c.get("/api/books/bank/back?s=nope-not-a-real-state-value")
    assert page.status_code == 200 and "not from Hoola" in page.text and "hoola-bank" in page.text
    assert E.allowed("viewer", "bank_feed") and not E.allowed("viewer", "bank_connect")
    assert E.allowed("accountant", "bank_sync") and not E.allowed("accountant", "bank_connect") and E.allowed("admin", "bank_connect")
    from app import bookschat as BC
    with pytest.raises(E.EntError):
        BC.do("someone-else", "bank_connect", {"workspace": ws})


def test_expiry_is_said_once(B, monkeypatch):
    from app.db import session
    from app.fin.models import FinBankLink
    ws = _setup()
    _fake(monkeypatch, lambda m, u, kw: (200, {"access": "AT"}) if u.endswith("/token/new/") else
          (200, {"status": "LN", "accounts": []}) if "/requisitions/" in u else (404, {}))
    with session() as s:
        s.add(FinBankLink(id="fbl_x", tenant_id=T, workspace_id=ws, partner="gocardless", country="GB", ext_ref="rq9", status="active",
                          expires_at=(date.today() + timedelta(days=3)).isoformat() + "T00:00:00+00:00"))
    from app import convs
    said = []
    monkeypatch.setattr(convs, "notice_chat", lambda t: "conv-updates")
    import app.agent.santosh as SA
    monkeypatch.setattr(SA, "_save", lambda conv, role, blocks, display="": said.append(display))
    B.tick()
    assert len(said) == 1 and "runs out in" in said[0] and "Renew" in said[0]
    B._last.clear()
    from app.db import session as ss
    with ss() as s2:
        s2.get(FinBankLink, "fbl_x").last_sync = ""
    B.tick()
    assert len(said) == 1                                                        # said once
    v = B.overview(T, ws)["links"][0]
    assert v["renew"] and v["status"] == "active"


def test_desk_has_bank_accounts():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "app/static/console/booksdesk.js").read_text()
    for k in ("bankCard", "connectPage", "bank_feed", "bank_connect", "data-bkfind", "data-bkdisc", "data-bksync", "bksender", "hoola-bank",
              "/api/books/bank-file", "Continue at my bank"):
        assert k in js, k


from tests.test_v0999_158_books_desk import bk, bk_server   # noqa: E402,F401  the real-server + Chromium fixture


def test_bank_accounts_in_a_real_browser(bk_server, monkeypatch):
    import os
    from app.config import get_settings
    from app.fin.desks import books_bank as Bb
    base, browser, key = bk_server
    shots = os.environ.get("HOOLA_SHOTS")
    st = get_settings()
    for k, v in {"public_base_url": base, "gocardless_secret_id": "id", "gocardless_secret_key": "key", "open_banking_ack": "gocardless",
                 "secret_key": st.secret_key or "test-key"}.items():
        monkeypatch.setattr(st, k, v)

    def h(m, url, kw):
        if url.endswith("/token/new/"):
            return 200, {"access": "AT"}
        if "/institutions/" in url:
            return 200, [{"id": "MONZO_X", "name": "Monzo"}, {"id": "HSBC_X", "name": "HSBC"}]
        if url.endswith("/agreements/enduser/"):
            return 201, {"id": "ag1"}
        if url.endswith("/requisitions/"):
            return 201, {"id": "rq1", "link": base + "/api/books/bank/back?s=" + kw["json"]["reference"]}   # the 'bank' sends her straight back
        if url.endswith("/requisitions/rq1/"):
            return 200, {"status": "LN", "accounts": ["acc1"]}
        if url.endswith("/details/"):
            return 200, {"account": {"iban": "GB29NWBK60161331926819", "currency": "GBP"}}
        if url.endswith("/transactions/"):
            return 200, {"transactions": {"booked": [{"transactionId": "t1", "bookingDate": TODAY, "debtorName": "ACME LTD",
                                                      "transactionAmount": {"amount": "250.00", "currency": "GBP"}}]}}
        return 200, {}
    _fake(monkeypatch, h)
    Bb._last.clear()
    ws = _setup()
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}'); localStorage.setItem('hoola.books.ws', '{ws}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/books#/bank")
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Bank accounts')", timeout=20000)
    assert "No bank account yet" in pg.inner_text("#mdPage")
    pg.click("button[data-go='bank/connect']")
    pg.wait_for_selector("[data-bkfind='GB']", timeout=10000)
    txt = pg.inner_text("#mdPage")
    for k in ("1. Bank connection", "2. Bank files", "3. Your bank's statement email", "4. Upload a statement", "/api/books/bank-file", "GoCardless"):
        assert k in txt, k
    pg.fill("#bkQ_GB", "mon")
    pg.click("[data-bkfind='GB']")
    pg.wait_for_function("() => document.querySelector('#bkBank_GB').options[0].text === 'Monzo'", timeout=10000)
    pg.fill("#bkName_GB", "Main current")
    if shots:
        pg.screenshot(path=f"{shots}/books-bank-connect.png", full_page=True)
    try:
        with pg.expect_popup(timeout=10000) as pop:
            pg.click("form[data-form=bkconnect] button[type=submit]")
    except Exception:
        pg.wait_for_timeout(2000)
        from app.db import session as _s
        from app.fin.models import FinBankLink as _L
        with _s() as s3:
            n = s3.query(_L).count()
        raise AssertionError(f"{pg.inner_text('#toast')!r} {errors} links={n} pages={len(ctx.pages)} {[p.url for p in ctx.pages]}")
    w = pop.value
    try:
        w.wait_for_url("**/api/books/bank/back**", timeout=10000)
        w.wait_for_load_state()
        assert "Bank connected" in w.inner_text("body")
    except Exception as e:      # the page closes itself 1.5 s after it says so
        assert "closed" in str(e).lower() or w.is_closed(), e
    pg.wait_for_function("() => location.hash === '#/bank' && document.querySelector('#mdPage').innerText.includes('Main current')", timeout=15000)
    txt = pg.inner_text("#mdPage")
    assert "Bank connection" in txt and "Connected" in txt and "ACME LTD" in txt, txt[:900]
    pg.goto(base + "/console/books#/bank/connect")
    pg.wait_for_selector("form[data-form=bksender]", timeout=10000)
    pg.fill("#bkSnd", "@hdfcbank.example")
    pg.fill("#bkSndA", "HDFC current")
    pg.fill("#bkSndP", "01011990")
    pg.click("form[data-form=bksender] button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#toast').innerText.includes('now go into HDFC current')", timeout=10000)
    pg.goto(base + "/console/books#/bank")
    pg.wait_for_function("() => document.querySelector('#mdPage').innerText.includes('Statements by email')", timeout=10000)
    if shots:
        pg.screenshot(path=f"{shots}/books-bank.png", full_page=True)
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.wait_for_timeout(300)
    wide = pg.evaluate("""() => [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > window.innerWidth + 1 && !(e.parentElement && e.parentElement.getBoundingClientRect().right > window.innerWidth + 1))
        .slice(0, 6).map(e => e.tagName + '.' + e.className + '#' + e.id + ' ' + getComputedStyle(e).position + ' ' + Math.round(e.getBoundingClientRect().right) + ' ' + (e.innerText || '').slice(0, 40))""")
    sw = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth, document.body.scrollWidth]")
    pg.goto(base + "/console/books#/today")
    pg.wait_for_selector("#mdPage .bk-4", timeout=10000)
    sw2 = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert sw[0] <= sw[1] + 1, (sw, sw2, wide)
    assert not errors, errors
    ctx.close()
