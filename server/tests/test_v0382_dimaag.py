"""v0.382 DIMAAG (App Phases 43-46): the app's logic engine end to end on a real built app - linked lists
(customer -> invoices -> lines), formulas + roll-ups, rules + unique keys, a workflow with a maker-checker approval
chain, triggers (notify / set / create / run), cascade + restrict deletes, scheduled jobs, SLA, a callable function,
Opus drafting (faked) with the checker's repair round, and her tap applying it."""
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

LISTS = [
    {"key": "customers", "label": "Customers", "rules": {"create": "admin", "read": "admin", "update": "admin", "delete": "admin"},
     "fields": [{"key": "name", "label": "Name", "type": "text", "required": True},
                {"key": "phone", "label": "Phone", "type": "phone"},
                {"key": "city", "label": "City", "type": "text"},
                {"key": "tier", "label": "Tier", "type": "choice", "options": ["normal", "gold"]},
                {"key": "billed", "label": "Billed", "type": "number"}]},
    {"key": "invoices", "label": "Invoices", "rules": {"create": "admin", "read": "admin", "update": "admin", "delete": "admin"},
     "fields": [{"key": "customer", "label": "Customer", "type": "ref", "to": "customers", "required": True},
                {"key": "date", "label": "Date", "type": "date"},
                {"key": "subtotal", "label": "Subtotal", "type": "number"},
                {"key": "discount", "label": "Discount", "type": "number"},
                {"key": "total", "label": "Total", "type": "number"},
                {"key": "due", "label": "Due date", "type": "date"},
                {"key": "status", "label": "Status", "type": "choice", "options": ["Draft"]},
                {"key": "priority", "label": "Priority", "type": "text"},
                {"key": "paid_on", "label": "Paid on", "type": "date"},
                {"key": "reminded", "label": "Reminded", "type": "text"}]},
    {"key": "lines", "label": "Lines", "rules": {"create": "admin", "read": "admin", "update": "admin", "delete": "admin"},
     "fields": [{"key": "invoice", "label": "Invoice", "type": "ref", "to": "invoices", "required": True},
                {"key": "item", "label": "Item", "type": "text", "required": True},
                {"key": "qty", "label": "Qty", "type": "number"},
                {"key": "rate", "label": "Rate", "type": "number"},
                {"key": "amount", "label": "Amount", "type": "number"}]},
    {"key": "followups", "label": "Follow-ups", "rules": {"create": "admin", "read": "admin", "update": "admin", "delete": "admin"},
     "fields": [{"key": "title", "label": "Title", "type": "text", "required": True},
                {"key": "invoice", "label": "Invoice", "type": "ref", "to": "invoices"}]},
]
LOGIC = {
    "relations": [
        {"name": "invoices", "from": "invoices", "field": "customer", "to": "customers", "label": "Invoices", "on_delete": "restrict"},
        {"name": "lines", "from": "lines", "field": "invoice", "to": "invoices", "label": "Items", "on_delete": "cascade"},
        {"name": "followups", "from": "followups", "field": "invoice", "to": "invoices", "label": "Follow-ups", "on_delete": "nullify"}],
    "formulas": [
        {"coll": "lines", "field": "amount", "expr": "round(qty * rate, 2)"},
        {"coll": "invoices", "field": "subtotal", "expr": "sum(lines.amount)"},
        {"coll": "invoices", "field": "total", "expr": "subtotal - discount"},
        {"coll": "invoices", "field": "discount", "expr": "disc(subtotal, customer.tier)"},
        {"coll": "invoices", "field": "due", "expr": "add_days(coalesce(date, today()), 15)"},
        {"coll": "customers", "field": "billed", "expr": "sum(where(invoices, \"status\", \"!=\", \"Cancelled\").total)"}],
    "rules": [{"coll": "lines", "check": "qty > 0", "message": "Quantity 1 ya zyada honi chahiye"},
              {"coll": "lines", "check": "rate <= 100000", "message": "Rate bahut zyada"}],
    "unique": [{"coll": "customers", "fields": ["phone"], "message": "Is phone ka customer pehle se hai"}],
    "labels": {"invoices": "customer"},
    "workflows": [{"coll": "invoices", "field": "status", "states": ["Draft", "Sent", "Approved", "Paid", "Cancelled"],
                   "initial": "Draft", "transitions": [
                       {"from": ["Draft"], "to": "Sent", "label": "Send", "who": ["staff"], "require": ["date"]},
                       {"from": ["Sent"], "to": "Approved", "label": "Approve", "who": ["staff"],
                        "approval": {"steps": [{"who": "staff", "label": "Manager"}, {"who": "admin", "label": "Director"}],
                                     "maker_checker": True, "when": "total > 1000"}},
                       {"from": ["Approved"], "to": "Paid", "label": "Mark paid", "who": ["admin"]},
                       {"from": "*", "to": "Cancelled", "label": "Cancel", "who": ["admin"]}],
                   "sla": [{"state": "Sent", "hours": 24, "notify": "admins", "move_to": "", "message": "Sent 24 ghante se pada hai"}]}],
    "triggers": [
        {"name": "Big line", "coll": "lines", "on": "create", "when": "amount > 5000",
         "do": [{"notify": "owner", "title": "Badi line {{item}}", "body": "{{money(amount)}}"}]},
        {"name": "Paid date", "coll": "invoices", "on": "enter:Paid", "do": [{"set": {"paid_on": "today()"}}]},
        {"name": "Priority", "coll": "invoices", "on": "change:total", "do": [{"run": "prio", "args": ["total"]}]},
        {"name": "Follow up", "coll": "invoices", "on": "enter:Sent",
         "do": [{"create": "followups", "values": {"title": "\"Call \" + customer.name", "invoice": "id"}, "owner": "none"}]}],
    "schedules": [{"name": "remind", "label": "Unpaid reminder", "every": "daily 09:00", "coll": "invoices",
                   "where": "status == \"Approved\"", "do": [{"set": {"reminded": "today()"}}]}],
    "functions": [
        {"name": "disc", "label": "Discount", "params": ["sub", "tier"],
         "body": "if tier == \"gold\" { return round(sub * 0.1, 2) }\nreturn 0",
         "tests": [{"args": [1000, "gold"], "expect": 100}, {"args": [1000, "normal"], "expect": 0}]},
        {"name": "prio", "label": "Priority", "params": ["t"],
         "body": "if t > 5000 { return {\"priority\": \"High\"} }\nreturn {\"priority\": \"Normal\"}",
         "tests": [{"args": [6000], "expect": {"priority": "High"}}]},
        {"name": "emi", "label": "EMI", "params": ["p", "months"], "callable": True,
         "body": "if months <= 0 { fail(\"Mahine 1 ya zyada\") }\nreturn round(p / months, 2)",
         "tests": [{"args": [1200, 12], "expect": 100}, {"args": [100, 0], "fails": True}]}],
}


def _acct(c, api, email, name):
    c.post(f"{api}/signup", json={"email": email, "password": "pass-" + name.lower() + "-1", "name": name})
    return {"Authorization": "Bearer " + c.post(f"{api}/login", json={"email": email, "password": "pass-" + name.lower() + "-1"}).json()["token"]}


def _setup(droid_env):
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    hr, hm, hb, hc = (_acct(c, api, e, n) for e, n in (("ravi@example.com", "Ravi"), ("meena@example.com", "Meena"),
                                                        ("boss@example.com", "Boss"), ("asha@example.com", "Asha")))
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    for e, role in (("ravi@example.com", "staff"), ("meena@example.com", "staff"), ("boss@example.com", "admin")):
        c.post(f"/api/apps/{aid}/members/{mem[e]['id']}/role", json={"role": role})
    hr, hm, hb = (_acct(c, api, e, n) for e, n in (("ravi@example.com", "Ravi"), ("meena@example.com", "Meena"), ("boss@example.com", "Boss")))
    got = c.put(f"/api/apps/{aid}/logic", json={"logic": LOGIC, "lists": LISTS}).json()
    assert got["ok"] is True, got
    return c, aid, api, hr, hm, hb, hc


def test_language_is_locked_and_budgeted():
    from app.appmaker.logic import lang as L
    assert L.evaluate("qty * rate", {"qty": 3, "rate": "12.5"}) == 37.5
    assert L.evaluate("sum(lines.amount)", {"lines": [{"amount": 10}, {"amount": 5.5}]}) == 15.5
    assert L.evaluate("money(1234567.5)") == "₹12,34,567.50"
    assert L.evaluate('status not in ["Done", "Cancelled"]', {"status": "New"}) is True
    for bad in ('__import__("os")', "open(\"/etc/passwd\")", "eval(\"1\")", "x.__class__.__mro__"):
        try:
            v = L.evaluate(bad, {"x": {"a": 1}})
            assert v is None                                         # attribute = dict key: nothing to reach
        except L.LogicError:
            pass
    body = L.parse_body("let x = 0\nfor i in range(2000) { for j in range(2000) { x = x + 1 } }\nreturn x")
    try:
        L.call_function({"f": ([], body)}, "f", [])
        raise AssertionError("must stop")
    except L.LogicError as e:
        assert "loop" in str(e)
    rec = L.parse_body("return f(n)")
    try:
        L.call_function({"f": (["n"], rec)}, "f", [1])
        raise AssertionError("must stop")
    except L.LogicError:
        pass
    try:
        L.evaluate('"a" + x', {"x": "b" * 15000}) and L.evaluate("x + x", {"x": "b" * 15000})
        raise AssertionError("must stop")
    except L.LogicError:
        pass


def test_checker_refuses_what_would_break(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker.logic import spec as SP
    sch = {"collections": LISTS}
    good = SP.check(LOGIC, sch)
    assert good["errors"] == [], good["errors"]
    f = [x["field"] for x in good["spec"]["formulas"] if x["coll"] == "invoices"]
    assert f.index("subtotal") < f.index("discount") < f.index("total")      # order from the dependencies
    bad = SP.check({"formulas": [{"coll": "lines", "field": "amount", "expr": "qty * price"},
                                 {"coll": "invoices", "field": "subtotal", "expr": "total + 1"},
                                 {"coll": "invoices", "field": "total", "expr": "subtotal + 1"},
                                 {"coll": "invoices", "field": "discount", "expr": "customer.nope"}],
                    "workflows": [{"coll": "invoices", "states": ["A", "B"], "transitions": [{"from": ["A"], "to": "Z"}]}],
                    "triggers": [{"name": "t", "coll": "lines", "on": "explode", "do": [{"notify": "x"}]}],
                    "functions": [{"name": "f", "params": ["a"], "body": "return a + b", "tests": []},
                                  {"name": "g", "params": ["a"], "body": "return a * 2", "tests": [{"args": [2], "expect": 5}]}]}, sch)
    e = "\n".join(bad["errors"])
    assert "'price'" in e and "ghoom" in e and "nope" in e and "'Z'" in e and "on:" in e and "'b'" in e
    del BE


def test_logic_end_to_end(droid_env, monkeypatch):
    notes = []
    from app.appmaker.android import service as AN
    monkeypatch.setattr(AN, "_note", lambda r, t: notes.append(t))
    pushes = []
    from app.appmaker import turant as TU
    monkeypatch.setattr(TU, "later", lambda r, ids, title, body, rid="": pushes.append((tuple(ids), title)))
    c, aid, api, hr, hm, hb, hc = _setup(droid_env)
    sch = c.get(f"{api}/schema").json()
    inv = next(x for x in sch["collections"] if x["key"] == "invoices")
    fi = {f["key"]: f for f in inv["fields"]}
    assert fi["customer"]["type"] == "ref" and fi["customer"]["to"] == "customers"
    assert fi["total"]["computed"] and fi["status"]["options"] == ["Draft", "Sent", "Approved", "Paid", "Cancelled"]
    assert inv["workflow"] == "status" and {"name": "lines", "coll": "lines", "field": "invoice", "label": "Items"} in inv["relations"]
    assert sch["approvals"] is True and sch["functions"] == [{"name": "emi", "label": "EMI", "params": ["p", "months"]}]
    # customers + unique phone
    gold = c.post(f"{api}/c/customers", json={"name": "Sharma Traders", "phone": "9876500001", "tier": "gold", "city": "Akola"}, headers=hr).json()
    r = c.post(f"{api}/c/customers", json={"name": "Copy", "phone": "9876500001"}, headers=hr)
    assert r.status_code == 409 and "pehle se" in r.json()["error"]
    # a ref must point to a real row of the right list
    assert c.post(f"{api}/c/invoices", json={"customer": "row_nope"}, headers=hr).status_code == 422
    i1 = c.post(f"{api}/c/invoices", json={"customer": gold["id"], "status": "Paid", "total": 1}, headers=hr).json()
    assert i1["status"] == "Draft" and i1["total"] == 0 and i1["_labels"]["customer"] == "Sharma Traders"
    assert i1["_actions"] == [{"to": "Sent", "label": "Send", "approval": False}]
    # lines: formulas, rules, roll-up to the invoice (discount via her function) and to the customer
    assert c.post(f"{api}/c/lines", json={"invoice": i1["id"], "item": "Rice", "qty": 0, "rate": 50}, headers=hr).status_code == 422
    l1 = c.post(f"{api}/c/lines", json={"invoice": i1["id"], "item": "Rice", "qty": 10, "rate": 55.5, "amount": 1}, headers=hr).json()
    assert l1["amount"] == 555
    c.post(f"{api}/c/lines", json={"invoice": i1["id"], "item": "Oil", "qty": 4, "rate": 1500}, headers=hr)
    rows = {x["id"]: x for x in c.get(f"{api}/c/invoices", headers=hr).json()["rows"]}
    assert rows[i1["id"]]["subtotal"] == 6555 and rows[i1["id"]]["discount"] == 655.5 and rows[i1["id"]]["total"] == 5899.5
    assert rows[i1["id"]]["priority"] == "High"                                     # trigger ran her function
    assert any("Badi line Oil" in n for n in notes)                                # owner told about the ₹6,000 line
    cust = c.get(f"{api}/c/customers", headers=hr).json()["rows"][0]
    assert cust["billed"] == 5899.5
    rel = c.get(f"{api}/c/invoices/{i1['id']}/related/lines", headers=hr).json()
    assert [x["item"] for x in rel["rows"]] == ["Rice", "Oil"] and rel["rel"]["label"] == "Items"
    assert c.get(f"{api}/c/invoices/{i1['id']}/related/lines", headers=hc).status_code == 404   # a customer cannot read it
    # workflow: Send needs a date; then a follow-up is created by the trigger
    r = c.post(f"{api}/c/invoices/{i1['id']}", json={"status": "Sent"}, headers=hr)
    assert r.status_code == 422 and "Date" in r.json()["error"]
    assert c.post(f"{api}/c/invoices/{i1['id']}", json={"status": "Paid"}, headers=hb).status_code == 422   # not a step from Draft
    s1 = c.post(f"{api}/c/invoices/{i1['id']}", json={"status": "Sent", "date": "2026-11-01"}, headers=hr).json()
    assert s1["status"] == "Sent" and s1["due"] == "2026-11-16"
    fu = c.get(f"{api}/c/followups", headers=hr).json()["rows"]
    assert fu[0]["title"] == "Call Sharma Traders" and fu[0]["invoice"] == i1["id"]
    # approval chain: Ravi asks; Ravi cannot approve his own ask; Meena (staff) = step 1; Ravi cannot do step 2; Boss (admin) = step 2
    a = c.post(f"{api}/c/invoices/{i1['id']}", json={"status": "Approved"}, headers=hr).json()
    assert a["status"] == "Sent" and a["approval"]["of"] == 2 and a["_pending"]["waiting_for"] == "Manager" and a["_actions"] == []
    aid1 = a["approval"]["id"]
    assert c.post(f"{api}/c/invoices/{i1['id']}", json={"status": "Approved"}, headers=hm).status_code == 409   # one at a time
    r = c.post(f"{api}/approvals/{aid1}", json={"decision": "approve"}, headers=hr)
    assert r.status_code == 403 and "maker-checker" in r.json()["error"]
    assert c.post(f"{api}/approvals/{aid1}", json={"decision": "approve"}, headers=hc).status_code == 403
    mine = c.get(f"{api}/approvals", headers=hm).json()["approvals"]
    assert mine[0]["can_decide"] and mine[0]["waiting_for"] == "Manager"
    st = c.post(f"{api}/approvals/{aid1}", json={"decision": "approve", "note": "ok"}, headers=hm).json()
    assert st["status"] == "pending" and st["step"] == 2
    assert c.post(f"{api}/approvals/{aid1}", json={"decision": "approve"}, headers=hm).status_code == 403    # one person = one step
    done = c.post(f"{api}/approvals/{aid1}", json={"decision": "approve"}, headers=hb).json()
    assert done["status"] == "approved"
    row = next(x for x in c.get(f"{api}/c/invoices", headers=hb).json()["rows"] if x["id"] == i1["id"])
    assert row["status"] == "Approved" and row["_actions"][0]["to"] == "Paid"
    # enter:Paid trigger sets paid_on; only admin may mark paid
    assert c.post(f"{api}/c/invoices/{i1['id']}", json={"status": "Paid"}, headers=hr).status_code == 403
    paid = c.post(f"{api}/c/invoices/{i1['id']}", json={"status": "Paid"}, headers=hb).json()
    assert paid["status"] == "Paid" and paid["paid_on"]
    # a small invoice needs no approval (approval.when = total > 1000)
    i2 = c.post(f"{api}/c/invoices", json={"customer": gold["id"], "date": "2026-11-01"}, headers=hr).json()
    c.post(f"{api}/c/lines", json={"invoice": i2["id"], "item": "Salt", "qty": 2, "rate": 20}, headers=hr)
    c.post(f"{api}/c/invoices/{i2['id']}", json={"status": "Sent"}, headers=hr)
    assert c.post(f"{api}/c/invoices/{i2['id']}", json={"status": "Approved"}, headers=hr).json()["status"] == "Approved"
    # deletes: a customer with invoices = restrict; an invoice = its lines go too (cascade), follow-ups keep but unlink
    r = c.delete(f"{api}/c/customers/{gold['id']}", headers=hb)
    assert r.status_code == 409 and "Invoices" in r.json()["error"]
    assert c.delete(f"{api}/c/invoices/{i1['id']}", headers=hb).json()["ok"]
    assert all(x["invoice"] != i1["id"] for x in c.get(f"{api}/c/lines", headers=hb).json()["rows"])
    fus = [x["invoice"] for x in c.get(f"{api}/c/followups", headers=hb).json()["rows"]]
    assert "" in fus and i1["id"] not in fus and i2["id"] in fus
    assert c.get(f"{api}/c/customers", headers=hb).json()["rows"][0]["billed"] == 36          # roll-up after the delete
    # callable function in the locked box
    assert c.post(f"{api}/fn/emi", json={"args": [1200, 12]}).json()["result"] == 100
    assert c.post(f"{api}/fn/emi", json={"args": [1200, 0]}).status_code == 422
    assert c.post(f"{api}/fn/disc", json={"args": [1, "gold"]}).status_code == 404               # not marked callable
    # schedule + SLA
    v = c.post(f"/api/apps/{aid}/logic/run/remind").json()
    assert v["acted"] == 1                                                                        # i2 is Approved
    assert c.post(f"/api/apps/{aid}/logic/run/remind").json()["acted"] == 0                      # once per row
    view = c.get(f"/api/apps/{aid}/logic").json()
    kinds = {a["kind"] for a in view["audit"]}
    assert {"approval_asked", "approval_approve", "move", "notify", "create", "schedule", "applied"} <= kinds
    assert view["on"] and any("Workflow (invoices)" in x for x in view["summary"])
    # off switch: the app behaves as before (no workflow guard)
    c.post(f"/api/apps/{aid}/logic/switch", json={"on": False})
    i3 = c.post(f"{api}/c/invoices", json={"customer": gold["id"], "status": "Paid"}, headers=hr).json()
    assert "_actions" not in i3
    c.post(f"/api/apps/{aid}/logic/switch", json={"on": True})


def test_schedule_slots_and_sla(droid_env, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from app.appmaker.logic import engine as LE
    at = datetime(2026, 11, 2, 4, 0, tzinfo=timezone.utc)                       # 09:30 IST Monday
    assert LE.due("daily 09:00", "2026-11-01T04:00:00+00:00", at) is True
    assert LE.due("daily 09:00", "2026-11-02T03:31:00+00:00", at) is False      # ran at 09:01 today
    assert LE.due("daily 10:00", "2026-11-01T05:00:00+00:00", at) is False      # today's slot not yet
    assert LE.due("weekly mon 09:00", "2026-10-26T04:00:00+00:00", at) is True
    assert LE.due("monthly 1 09:00", "2026-11-01T03:31:00+00:00", at) is False
    assert LE.due("hourly", "2026-11-02T03:20:00+00:00", at) is True
    c, aid, api, hr, hm, hb, hc = _setup(droid_env)
    pushes = []
    from app.appmaker import turant as TU
    monkeypatch.setattr(TU, "later", lambda r, ids, title, body, rid="": pushes.append(title))
    cu = c.post(f"{api}/c/customers", json={"name": "Old", "phone": "9876500002"}, headers=hr).json()
    i = c.post(f"{api}/c/invoices", json={"customer": cu["id"], "date": "2026-10-01"}, headers=hr).json()
    c.post(f"{api}/c/invoices/{i['id']}", json={"status": "Sent"}, headers=hr)
    from app.appmaker.models import AppProject
    from app.db import session
    old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    LE.store(_app(aid), i["id"], {"_wf_at": old})
    assert LE.sla_check(_app(aid)) == 1 and any("Der ho rahi" in p for p in pushes)
    assert LE.sla_check(_app(aid)) == 0                                          # told once per waiting spell
    del AppProject, session


def _app(aid):
    from app.appmaker.models import AppProject
    from app.db import session
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    return r


def test_opus_draft_repair_and_her_tap(droid_env):
    from app.appmaker.logic import service as LS
    c, aid, api, hr, hm, hb, hc = _setup(droid_env)
    calls = []

    def fake(system, prompt):
        calls.append(prompt)
        if len(calls) == 1:                                    # first try: a field that does not exist
            return {"summary": "Order par 10% tax", "fields": [{"coll": "orders", "key": "tax", "label": "Tax", "type": "number"}],
                    "logic": {"formulas": [{"coll": "orders", "field": "tax", "expr": "totl * 0.1"}]}}
        assert "totl" in prompt and "checker" in prompt        # the repair round sees the checker's words
        return {"summary": "Order par 10% tax", "fields": [{"coll": "orders", "key": "tax", "label": "Tax", "type": "number"}],
                "logic": {**LOGIC, "formulas": LOGIC["formulas"] + [{"coll": "orders", "field": "tax", "expr": "round(total * 0.1, 2)"}]}}
    r = _app(aid)
    d = LS.draft(r, "har order par 10% tax dikhao", ask=fake)
    assert d["ready"] and d["errors"] == [] and len(calls) == 2 and any("orders.tax" in x for x in d["lines"])
    assert c.post(f"/api/apps/{aid}/logic/apply", json={"hash": "wrong"}).status_code == 409   # only the exact draft she saw
    got = c.post(f"/api/apps/{aid}/logic/apply", json={"hash": d["hash"]}).json()
    assert got["rev"] >= 2 and any("orders.tax" in x for x in got["schema_changes"])
    sch = c.get(f"{api}/schema").json()
    assert next(f for f in next(x for x in sch["collections"] if x["key"] == "orders")["fields"] if f["key"] == "tax")["computed"]
    t = c.post(f"/api/apps/{aid}/logic/test", json={"coll": "orders", "expr": "round(2.345, 2) + 1"}).json()
    assert t == {"ok": True, "value": 3.35}


def test_customer_cancels_own_order_through_the_workflow_and_stock_comes_back(droid_env):
    """A customer's own allowed step works (customers never write staff fields - the engine moves it), a step she is not
    allowed is refused, and a workflow Cancel gives back the order's stock exactly like the old status chip did."""
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    ha = _acct(c, api, "asha@example.com", "Asha")
    hz = _acct(c, api, "zoya@example.com", "Zoya")
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    c.put(f"/api/apps/{aid}/stock", json={"items": {p1["id"]: {"qty": 5}}})
    wf = {"workflows": [{"coll": "orders", "field": "status", "states": ["New", "Accepted", "Delivered", "Cancelled"], "initial": "New",
                         "transitions": [{"from": ["New"], "to": "Cancelled", "label": "Cancel", "who": ["row_owner", "staff"]},
                                         {"from": ["New"], "to": "Accepted", "label": "Accept", "who": ["staff"]},
                                         {"from": ["Accepted"], "to": "Delivered", "label": "Deliver", "who": ["staff"]}]}],
          "rules": [{"coll": "orders", "check": "len(phone) == 10", "message": "Phone 10 ank"}]}
    assert c.put(f"/api/apps/{aid}/logic", json={"logic": wf}).json()["ok"]
    o = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 2}]}, headers=ha).json()
    assert o["status"] == "New" and o["_actions"] == [{"to": "Cancelled", "label": "Cancel", "approval": False}]
    assert {p["id"]: p for p in c.get(f"/api/apps/{aid}/stock").json()["products"]}[p1["id"]]["qty"] == 3
    assert c.post(f"{api}/c/orders/{o['id']}", json={"status": "Accepted"}, headers=ha).status_code == 403    # staff step
    assert c.post(f"{api}/c/orders/{o['id']}", json={"status": "Cancelled"}, headers=hz).status_code == 404    # not her row
    done = c.post(f"{api}/c/orders/{o['id']}", json={"status": "Cancelled"}, headers=ha).json()
    assert done["status"] == "Cancelled" and done["_actions"] == []
    assert {p["id"]: p for p in c.get(f"/api/apps/{aid}/stock").json()["products"]}[p1["id"]]["qty"] == 5    # given back once
    assert c.post(f"{api}/c/orders/{o['id']}", json={"status": "New"}, headers=ha).status_code in (403, 422)


def test_kits_carry_the_logic_pieces():
    from pathlib import Path
    from app.appmaker.android import gen as AG
    from app.appmaker.ios import gen as IG
    base = Path(__file__).resolve().parents[1] / "app" / "appmaker"
    kt = (base / "android/template/app/src/main/java/hoola/kit/Logic.kt").read_text()
    sw = (base / "ios/template/Sources/Kit/Logic.swift").read_text()
    for name in ("fun RefField(", "fun WorkflowBox(", "fun RelatedBlock(", "fun AutoForm(", "fun ApprovalsScreen(", "fun DataScreen("):
        assert name in kt, name
    for name in ("struct RefField", "struct WorkflowBox", "struct RelatedBlock", "struct AutoForm", "struct ApprovalsScreen", "struct DataScreen"):
        assert name in sw, name
    assert {"hoola_approvals", "hoola_data"} <= set(AG.KIT_SCREENS) and {"hoola_approvals", "hoola_data"} <= set(IG.KIT_SCREENS)
    acc = (base / "android/template/app/src/main/java/hoola/kit/Accounts.kt").read_text()
    assert "WorkflowBox(coll, r)" in acc and "RelatedBlock(coll, r)" in acc and "Logic.show(r, f)" in acc
    assert "/approvals/" in kt and "/related/" in kt and kt.count("{") == kt.count("}")
    assert sw.count("{") == sw.count("}")
    from app.appmaker.android import prompts as AP
    line = AP.backend_line({"collections": [{"key": "lines", "rules": {"create": "admin"},
                                             "fields": [{"key": "invoice", "type": "ref", "to": "invoices"}]}]})
    assert "invoice[ref:invoices]" in line
