"""v0.109 Paisa bhejo: the UPI app's answer (or her word) closes the transfer; no more 'awaiting_payment' forever."""
import pytest
from sqlalchemy import select


@pytest.fixture
def bz(env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://santosh.example.in")
    monkeypatch.setenv("BAZAR_ENV", "dev")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bazar import config as bzc, security
    bzc.reset_settings()
    security._vault = None
    from app.bazar import service
    service.set_executors(None)
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        conv = c.id
    yield {"svc": service, "conv": conv}
    bzc.reset_settings()
    security._vault = None
    service.set_executors(None)


def _send(bz, pack="bhim", amount=500):
    svc, conv = bz["svc"], bz["conv"]
    svc.add_contact("default", "Priya", upi_id="priya.demo@okaxis")
    r = svc.run("default", conv, pack, "send_money", {"to": "Priya", "amount_rupees": amount, "note": "dinner"})
    return svc.decide("default", r["approval_id"], "approve")["open"]


def _txn(ref):
    from app.bazar.db import Transaction
    from app.db import session
    with session() as s:
        t = s.scalars(select(Transaction).where(Transaction.txn_ref == ref)).first()
        return t.status, dict(t.meta or {}), t.provider_ref


def _events(conv, kind):
    from app.db import Event, session
    with session() as s:
        from app.db import Event as E
        return [e.payload for e in s.scalars(select(E).where(E.conversation_id == conv, E.kind == kind).order_by(E.id)).all()]


def test_parse_npci_strings():
    from app.bazar.upiresult import parse
    r = parse("txnId=AXI123456789&responseCode=00&Status=SUCCESS&txnRef=SNTABC&ApprovalRefNo=612345678901")
    assert r["status"] == "SUCCESS" and r["approval_ref"] == "612345678901" and r["txn_ref"] == "SNTABC"
    assert parse("Status=FAILURE&responseCode=ZM")["status"] == "FAILURE"
    assert parse("status=submitted")["status"] == "SUBMITTED"
    assert parse("")["status"] == "UNKNOWN" and parse("garbage")["status"] == "UNKNOWN"
    assert parse("txnId=X1&responseCode=00")["status"] == "SUCCESS"


def test_open_carries_ref_payee_amount_and_success_closes_it(bz):
    op = _send(bz)
    assert op["kind"] == "upi" and op["txn_ref"] and op["vpa"] == "priya.demo@okaxis" and op["amount"] == "₹500"
    assert "tr=" + op["txn_ref"] in op["url"] and "am=500.00" in op["url"]
    st, meta, _ = _txn(op["txn_ref"])
    assert st == "awaiting_payment" and meta["package"] == "in.org.npci.upiapp"
    from app.bazar import upiresult
    out = upiresult.record("default", op["txn_ref"],
                           f"txnId=YBL1&responseCode=00&Status=SUCCESS&txnRef={op['txn_ref']}&ApprovalRefNo=612345678901", "ok")
    assert out["status"] == "completed" and "...8901" in out["say"] and "✅" in out["say"]
    st, meta, pref = _txn(op["txn_ref"])
    assert st == "completed" and meta["upi"]["said_by"] == "app" and pref == "612345678901"
    # a late empty report never undoes it
    assert upiresult.record("default", op["txn_ref"], "", "none")["unchanged"]
    cards = _events(bz["conv"], "upi_result")
    assert cards and cards[-1]["status"] == "completed" and cards[-1]["ask"] is False


def test_failure_reason_and_block_offers_copy(bz):
    op = _send(bz)
    from app.bazar import upiresult
    out = upiresult.record("default", op["txn_ref"], "Status=FAILURE&responseCode=U16", "ok")
    assert out["status"] == "failed" and out["card"]["blocked"] and "risk" in out["say"] and "kuch nahi kata" in out["say"]
    op2 = _send(bz, amount=200)
    out2 = upiresult.record("default", op2["txn_ref"], "Status=FAILURE&responseCode=ZM", "ok")
    assert out2["status"] == "failed" and not out2["card"]["blocked"] and "PIN galat" in out2["say"]


def test_no_answer_asks_her_then_her_word_counts(bz):
    op = _send(bz)
    from app.bazar import upiresult
    out = upiresult.record("default", op["txn_ref"], "", "cancelled")
    assert out["status"] == "awaiting_payment" and out["card"]["ask"] and out["card"]["blocked"]
    out = upiresult.record("default", op["txn_ref"], answer="done")
    assert out["status"] == "completed" and "aapne bataya" in out["say"]
    st, meta, _ = _txn(op["txn_ref"])
    assert meta["upi"]["said_by"] == "owner"
    op2 = _send(bz, amount=300)
    upiresult.record("default", op2["txn_ref"], "status=SUBMITTED", "ok")
    assert _txn(op2["txn_ref"])[0] == "pending"
    assert upiresult.record("default", op2["txn_ref"], answer="not")["status"] == "failed"


def test_other_owner_and_bad_input_refused(bz):
    op = _send(bz)
    from app.bazar import upiresult
    from app.bazar.connectors.base import ToolError
    with pytest.raises(ToolError):
        upiresult.record("someone-else", op["txn_ref"], "Status=SUCCESS", "ok")
    with pytest.raises(ToolError):
        upiresult.record("default", "SNTNOPE", "Status=SUCCESS", "ok")
    with pytest.raises(ToolError):
        upiresult.record("default", op["txn_ref"], answer="maybe")
    # a response naming another reference is not trusted
    out = upiresult.record("default", op["txn_ref"], "Status=SUCCESS&txnId=1&txnRef=SNTOTHER", "ok")
    assert out["status"] == "awaiting_payment" and out["card"]["ask"]


def test_api_and_catalog_package(bz):
    from fastapi.testclient import TestClient
    from app.main import app
    op = _send(bz)
    c = TestClient(app)
    r = c.post("/api/bazar/upi/result", json={"txn_ref": op["txn_ref"], "answer": "done"})
    assert r.status_code == 200 and r.json()["status"] == "completed"
    assert c.post("/api/bazar/upi/result", json={"txn_ref": "SNTNOPE", "answer": "done"}).status_code == 400
    cat = bz["svc"].catalog("default")
    pay = next(s for s in cat["top"] if s["id"] == "pay")
    pk = {p["pack_id"]: p.get("android_package") for p in pay["items"]}
    assert pk.get("phonepe") == "com.phonepe.app" and pk.get("google-pay") == "com.google.android.apps.nbu.paisa.user"


def test_v120_phonepe_goes_copy_and_pay_and_apps_learn(bz):
    """v0.120 PhonePe refuses payment links to a person ('security reasons'): it opens without a link, UPI ID copied."""
    op = _send(bz, pack="phonepe")
    assert op["kind"] == "upi_copy" and op["url"] == "" and op["vpa"] == "priya.demo@okaxis" and op["package"] == "com.phonepe.app"
    st, meta, _ = _txn(op["txn_ref"])
    assert st == "awaiting_payment" and meta["mode"] == "copy"
    cards = _events(bz["conv"], "upi_result")
    assert cards[-1]["ask"] and cards[-1]["mode"] == "copy"
    from app.bazar import upiresult
    assert upiresult.record("default", op["txn_ref"], answer="done")["status"] == "completed"
    # BHIM still gets the link; when she says it refused, BHIM learns copy-and-pay too
    op2 = _send(bz, pack="bhim", amount=200)
    assert op2["kind"] == "upi" and op2["url"].startswith("upi://pay")
    upiresult.record("default", op2["txn_ref"], answer="blocked")
    op3 = _send(bz, pack="bhim", amount=100)
    assert op3["kind"] == "upi_copy"
    # a link that worked in an app marks it ok again (beats the built-in list)
    from app.bazar.db import User
    from app.db import session
    with session() as s:
        u = s.get(User, "default")
        u.profile = {**(u.profile or {}), "upi_link_blocked": {"com.phonepe.app": "ok"}}
    op4 = _send(bz, pack="phonepe", amount=50)
    assert op4["kind"] == "upi"
