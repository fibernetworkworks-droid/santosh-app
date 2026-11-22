"""v0.999.61 HOOLA WALLET (owner: "AI WALLET ... WITH APPROVAL FROM USER -- ORDERING DAILY NEED, BILL PAYMENTS, FOOD ORDER"
+ "ENTIRE WORLD", design claude.ai/artifact/6saoWTun5YqusMghbLzYgn, "GO BUILD ALL"): Hoola asks to pay, only her phone
approves; her limits are checked in code before she is ever asked; Hoola holds no money."""
import asyncio
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"


@pytest.fixture
def W(env, monkeypatch):
    from app import wallet
    monkeypatch.setattr(wallet, "_wake", lambda *a, **k: None)
    monkeypatch.setattr(wallet, "_announce", lambda *a, **k: None)
    wallet.setup("t1", "IN", "each", 1_000_000, ["groceries", "food", "bills"])
    return wallet


def _ask(W, amount=48600, cat="groceries", title="Weekly groceries", shop="Zepto", url="https://www.zeptonow.com/cart"):
    return W.request("t1", "c1", shop, url, title, [{"name": "Milk", "qty": 2, "amount": 13600}], amount, cat)


def test_inside_the_rules_waits_for_her(W):
    p = _ask(W)
    assert p["status"] == "waiting" and p["amount_text"] == "₹ 486" and p["expires"]
    assert p["new_shop"] is True                                        # first time at this shop: marked on the card


def test_outside_the_rules_is_never_asked(W):
    assert _ask(W, amount=250_000)["status"] == "stopped"               # over one payment (Rs 2,000)
    assert "per-payment" in _ask(W, amount=250_000)["reason"]
    assert "switched off" in _ask(W, cat="shopping")["reason"]
    assert _ask(W, cat="loan")["status"] == "stopped"
    for t in ("send money to Ramesh", "gift card", "bitcoin top up", "mutual fund SIP", "betting credits"):
        assert "never pays" in _ask(W, title=t)["reason"], t
    W.set_limits("t1", {"paused": True})
    assert _ask(W)["reason"] == "You paused all spending."


def test_monthly_and_category_limits_count_what_was_paid(W):
    W.set_limits("t1", {"per_buy": 500_000, "per_day": 2_000_000, "cats": {"food": {"limit": 100_000}}})
    a = _ask(W, amount=90_000, cat="food", title="Dinner")
    W.decide("t1", a["id"], True, True)
    W.finish("t1", a["id"], True, "Z1")
    assert "food orders limit" in _ask(W, amount=20_000, cat="food", title="Lunch")["reason"]
    assert W.overview("t1")["spent"]["by"]["food"] == 90_000


def test_approving_needs_her_unlocked_phone_and_a_computer_cannot(W):
    p = _ask(W)
    with pytest.raises(W.WalletError, match="unlocked phone"):
        W.decide("t1", p["id"], True, False)
    assert W.decide("t1", p["id"], True, True)["status"] == "approved"
    with pytest.raises(W.WalletError, match="already approved"):
        W.decide("t1", p["id"], True, True)


def test_a_linked_phone_must_sign_this_payment(W, monkeypatch):
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda t: True)
    p = _ask(W)
    with pytest.raises(W.WalletError, match="fingerprint_needed"):
        W.decide("t1", p["id"], True, True)                             # unlocked alone is not enough
    seen = {}
    monkeypatch.setattr(ak, "verify", lambda t, kind, target, proof: seen.update(kind=kind, target=target, proof=proof))
    assert W.decide("t1", p["id"], True, False, {"challenge_id": "x"})["status"] == "approved"
    assert seen == {"kind": "wallet", "target": p["id"], "proof": {"challenge_id": "x"}}


def test_the_fingerprint_signs_the_payment_as_it_is(W):
    from app import approvekey as ak
    p = _ask(W)
    digest, show = ak.card_digest("wallet", p["id"], "t1")
    assert show["amount"] == "₹ 486" and show["payee"] == "Zepto" and len(digest) == 64
    assert ak.needed.__code__.co_consts and "wallet" in str(ak.needed.__code__.co_consts)
    W.decide("t1", p["id"], False, False)
    with pytest.raises(ak.ApproveError):
        ak.card_digest("wallet", p["id"], "t1")                          # not pending any more = nothing to sign


def test_no_never_needs_the_phone_and_expiry(W):
    p = _ask(W)
    assert W.decide("t1", p["id"], False, False)["status"] == "declined"
    q = _ask(W)
    from app.db import session
    with session() as s:
        s.get(W.WalletPayment, q["id"]).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    with pytest.raises(W.WalletError, match="expired"):
        W.decide("t1", q["id"], True, True)


def test_limits_are_checked_again_when_she_approves(W):
    p = _ask(W)
    W.set_limits("t1", {"per_buy": 10_000})
    out = W.decide("t1", p["id"], True, True)
    assert out["status"] == "stopped" and "per-payment" in out["reason"]


def test_paid_marks_the_bill_and_the_shop_becomes_known(W):
    b = W.add_bill("t1", "Electricity, home", "Electricity", "https://wss.mahadiscom.in", "440122334455", "2026-11-28", 85000)
    assert b["account"].endswith("4455") and "4401223" not in b["account"]
    from app.db import session
    with session() as s:
        assert "440122334455" not in (s.get(W.WalletBill, b["id"]).account_sealed or "")
    p = W.pay_bill("t1", "c1", b["id"])
    assert p["category"] == "bills" and p["status"] == "waiting"
    W.decide("t1", p["id"], True, True)
    with pytest.raises(W.WalletError):
        W.finish("t1", "nope", True)
    assert W.finish("t1", p["id"], True, "MSEB-1")["status"] == "paid"
    assert W.overview("t1")["bills"][0]["status"] == "paid"
    q = W.request("t1", "c1", "MSEDCL", "https://wss.mahadiscom.in/pay", "Bill", [], 1000, "bills")
    assert q["new_shop"] is False


def test_hoola_never_holds_money(W, monkeypatch):
    with pytest.raises(W.WalletError, match="licensed payment partner"):
        W.setup("t1", "IN", "balance", 100, ["groceries"])
    assert W.overview("t1")["balance"] is None
    assert W.setup("t2", "US", "each", 50_000, ["food"])["symbol"] == "$"
    with pytest.raises(W.WalletError):
        W.setup("t3", "XX", "each", 1, [])


def test_the_tool_asks_and_can_never_approve(W):
    from app.agent import tools
    from app.agent.tools import Ctx, ToolError
    t = next(x for x in tools.TOOLS if x["name"] == "hoola_wallet")
    assert "approve" not in t["input_schema"]["properties"]["action"]["enum"]
    assert set(t["input_schema"]["properties"]["action"]["enum"]) == {"status", "request", "paid", "failed", "bills", "pay_bill"}
    h = tools.HANDLERS["hoola_wallet"]
    r = asyncio.run(h(Ctx("t1", "c1"), "request", shop="Zepto", url="https://zeptonow.com", title="Milk", amount=68, category="groceries"))
    assert r["status"] == "waiting" and r["amount"] == 6800 and "Do not pay yet" in r["say"]
    r = asyncio.run(h(Ctx("t1", "c1"), "request", shop="X", title="gift card", amount=500, category="shopping"))
    assert r["status"] == "stopped" and "do not pay" in r["say"]
    with pytest.raises(ToolError):
        asyncio.run(h(Ctx("t1", "c1", actor="customer:9"), "status"))
    assert len(tools.TOOLS) == 637   # + books_accounts (v0.999.134 F3); + household_money (v0.999.129 F2)


def test_routes_and_header(env, monkeypatch):
    from app import wallet
    monkeypatch.setattr(wallet, "_wake", lambda *a, **k: None)
    monkeypatch.setattr(wallet, "_announce", lambda *a, **k: None)
    from app.main import app
    c = TestClient(app)
    assert c.get("/api/wallet").json()["exists"] is False
    assert c.post("/api/wallet/setup", json={"region": "IN", "mode": "balance", "monthly": 100}).status_code == 409
    assert c.post("/api/wallet/setup", json={"region": "IN", "mode": "each", "monthly": 1_000_000, "cats": ["groceries"]}).json()["exists"]
    assert c.post("/api/wallet/add-money").status_code == 409
    p = wallet.request("default", "", "Zepto", "", "Milk", [], 6800, "groceries")
    r = c.post(f"/api/wallet/payments/{p['id']}/decide", json={"approve": True})
    assert r.status_code == 409 and "unlocked phone" in r.json()["detail"]   # the console never sends the header
    r = c.post(f"/api/wallet/payments/{p['id']}/decide", json={"approve": True}, headers={"X-Hoola-Unlocked": "1"})
    assert r.json()["status"] == "approved"
    b = c.post("/api/wallet/bills", json={"name": "Water", "amount": 30000}).json()
    assert c.delete(f"/api/wallet/bills/{b['id']}").json()["ok"] is True


def test_push_only_while_waiting():
    from app import push
    assert "wallet_pay" in push.PUSH_KINDS
    t = push.render("wallet_pay", {"status": "waiting", "amount_text": "₹ 486", "shop": "Zepto"})
    assert t and "486" in t[1] and "Zepto" in t[1]
    assert not push.render("wallet_pay", {"status": "paid", "amount_text": "₹ 486", "shop": "Zepto"})


def test_console_and_phone_are_wired():
    html = (CON / "v2.html").read_text()
    assert 'id="v-wallet"' in html and re.search(r"wallet\.js\?v=", html) and re.search(r"wallet\.css\?v=", html)
    js = (CON / "v2.js").read_text()
    assert "['wallet','Hoola Wallet']" in js and "WALLET?.open($('#walletview'))" in js
    w = (CON / "wallet.js").read_text()
    assert "/to-phone" in w and "x-hoola-unlocked" not in w.lower()        # a computer can never approve
    assert "data-v=" not in w and 'class="hc"' not in w
    dart = (ROOT / "lib" / "ui" / "wallet" / "hoola_wallet.dart").read_text()
    assert "walletDecide" in dart and "requestUnlock" in dart and "Color(0x" not in dart
    assert "withValues(" not in dart                                     # not on the Flutter CI builds with (3.24)
    api = (ROOT / "lib" / "api.dart").read_text()
    assert "_withFingerprint('wallet'" in api and "'X-Hoola-Unlocked': '1'" in api
    tools = (ROOT / "lib" / "ui" / "shell" / "hoola_tools.dart").read_text()
    assert "HoolaWalletScreen(app: app)" in tools


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.135"
    assert "version: 0.999.135+1130" in (ROOT / "pubspec.yaml").read_text()
