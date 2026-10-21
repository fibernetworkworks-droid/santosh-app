"""v0.67 Hoola Computer Operator, end to end on the fictional Demo Seva Portal (from the owner's hoola-browser tests).

A scripted brain plays the model and a scripted owner answers on the phone (cards + live view).
1. First time: research the help page, password / CAPTCHA / Aadhaar / OTP typed by the OWNER straight into the page
   (Hoola is refused when it tries), a 2-page form with a site error that gets fixed, a photo upload from her own
   Hoola file, payment pressed by the owner herself in the live view, acknowledgement PDF -> her file, learned recipe.
2. Replay as a real background job (fake brain): fresh person, pauses only for her steps.
3. Site redesign: still works. Button renamed: handed back to the brain, which does it and resumes.
4. Safety: submit needs her tap (and only for that button), payment never pressed by Hoola, local sites blocked,
   uploads only her own files, nothing secret in recipes / logs / anything the model saw.
"""
import asyncio
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import operator_portal as portal  # noqa: E402

try:
    import playwright  # noqa: F401
    HAVE_PW = True
except ImportError:
    HAVE_PW = False
pytestmark = pytest.mark.skipif(not HAVE_PW, reason="needs playwright + chromium")

T = "default"
PASSWORD, AADHAAR = "Demo@123", "123412341234"


@pytest.fixture
def site(env, monkeypatch):
    monkeypatch.setenv("OPERATOR_ALLOW_PRIVATE", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    portal.STATE.update(layout="a", submissions=[], sessions={})
    srv = portal.serve(0)
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    from app.operator import service as ops
    ops._ops.clear()
    ops._cancel.clear()


def ref(page: str, name: str, role: str | None = None) -> str:
    for m in re.finditer(r'\[([\w]+)\] (\w+) "([^"]*)"', page):
        if name.lower() in m.group(3).lower() and (role is None or m.group(2) == role):
            return m.group(1)
    raise AssertionError(f"no element like {role} '{name}' in page:\n{page[:1500]}")


SEEN: list[str] = []     # everything the "model" got back from tools


async def call(job, tool, **a):
    from app.operator import service as ops
    out = await ops._tool(job, tool, a)
    SEEN.append(json.dumps(out, default=str) if not isinstance(out, str) else out)
    return out


def page_of(r):
    return r if isinstance(r, str) else (r.get("page") or json.dumps(r.get("changes", {})))


async def owner(person: dict, stop: asyncio.Event, answered: list):
    """The owner on her phone: answers every request (types secrets / OTP / CAPTCHA into the page, presses pay herself)."""
    from app.operator import service as ops
    while not stop.is_set():
        have = ops._ops.get(T)
        for a in list(have[1].approvals.values()) if have else []:
            if a.status != "pending":
                continue
            op = have[1]
            s = op.sessions.get("main")
            name = (s.refs.get(a.ref) or {}).get("name", "") if (s and a.ref) else ""
            ans = ""
            if a.kind == "captcha":
                ans = portal.STATE["last_captcha"]
            elif a.kind == "otp":
                ans = portal.STATE["last_otp"]
            elif a.kind == "secret":
                ans = PASSWORD if "password" in name.lower() else person["aadhaar"]
            elif a.kind == "payment":
                box = await s.page.locator(f'[data-hoola-ref="{a.ref}"]').bounding_box()
                await ops.owner_input(T, "click", box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                await asyncio.sleep(0.6)
            await ops.resolve(T, a.id, "approved" if person.get("approve", True) else "rejected", ans)
            answered.append(a.kind)
        await asyncio.sleep(0.1)


async def _first_run(site: str, photo_id: str):
    from app.operator import service as ops
    v = ops.start(T, "Demo Seva Portal par Meghana Ingle ke liye Form D-49 card apply karo", site + "/", [photo_id])
    assert v["status"] == "queued"
    op = await ops.operator(T)
    job = ops.Job(ops._row(v["id"]), op, ops.memory(T))
    ops._set(v["id"], status="running")
    stop, answered = asyncio.Event(), []
    who = asyncio.create_task(owner({"aadhaar": AADHAAR}, stop, answered))
    try:
        assert not (await call(job, "recipe_find", query="Form D-49 card apply"))["recipes"]
        r = await call(job, "open", url=site + "/")
        doc = await call(job, "open", url=site + "/docs/how-to-apply")
        assert "12-digit Aadhaar" in doc["page"]
        assert (await call(job, "playbook_save", task="Form D-49 on Demo Seva Portal", steps_markdown="1. Login\n2. Details",
                           sources=[site + "/docs/how-to-apply"]))["ok"]
        r = await call(job, "open", url=site + "/login")
        p = r["page"]
        assert "CAPTCHA ON PAGE" in p and "sensitive" in p
        await call(job, "fill", ref=ref(p, "User ID"), value="demo", var="user_id")
        blocked = await call(job, "fill", ref=ref(p, "Password"), value=PASSWORD)
        assert blocked["blocked"] == "secret"                      # Hoola never types a password
        assert (await call(job, "fill", ref=ref(p, "characters shown"), value="ABCDE"))["blocked"] == "captcha"
        w = await call(job, "ask_owner", kind="secret", reason="Portal ka password bhariye", ref=ref(p, "Password"))
        assert w["status"] == "approved" and PASSWORD not in json.dumps(w)
        w = await call(job, "ask_owner", kind="captcha", reason="Photo wale akshar bhariye", ref=ref(p, "characters shown"))
        r = await call(job, "click", ref=ref(w["page"], "Login", "button"))
        p = r["page"]
        assert "Applicant details" in p, p[:500]
        await call(job, "select", ref=ref(p, "Title"), option="Smt")
        await call(job, "fill", ref=ref(p, "Last name"), value="Ingle", var="last_name")
        await call(job, "fill", ref=ref(p, "First name"), value="Meghana", var="first_name")
        await call(job, "fill", ref=ref(p, "Date of birth"), value="15/08/1990", var="dob")
        await call(job, "check", ref=ref(p, "Female", "radio"))
        await call(job, "fill", ref=ref(p, "Father"), value="Anil Ingle", var="father_name")
        assert (await call(job, "fill", ref=ref(p, "Aadhaar"), value=AADHAAR))["blocked"] == "id"   # v0.75: by locker reference only
        await call(job, "ask_owner", kind="secret", reason="Apna Aadhaar number bhariye", ref=ref(p, "Aadhaar"))
        await call(job, "fill", ref=ref(p, "Email"), value="meghana@example.com", var="email")
        await call(job, "fill", ref=ref(p, "Mobile"), value="98900", var="mobile")
        r = await call(job, "click", ref=ref(p, "Next", "button"))
        assert any("10 digits" in a for a in r.get("alerts", [])), str(r)[:600]    # the site's error comes back
        p = r.get("page") or await call(job, "page")
        assert "•••" in p                                   # what she typed is masked when the page comes back
        await call(job, "fill", ref=ref(p, "Mobile"), value="9890012345", var="mobile")
        a2 = ref(p, "Aadhaar")
        if "•••" not in re.search(rf"\[{a2}\][^\n]*", p).group(0):
            await call(job, "ask_owner", kind="secret", reason="Aadhaar dobara", ref=a2)
        r = await call(job, "click", ref=ref(p, "Next", "button"))
        p = r["page"]
        assert "Address and documents" in p, p[:600]
        await call(job, "fill", ref=ref(p, "Flat"), value="Khanapur Ves", var="address_line")
        await call(job, "fill", ref=ref(p, "Area"), value="Akot", var="area")
        await call(job, "fill", ref=ref(p, "City"), value="Akola", var="city")
        await call(job, "select", ref=ref(p, "State"), option="maharashtra")
        await call(job, "fill", ref=ref(p, "PIN code"), value="444101", var="pin_code")   # "PIN code" is not a PIN
        bad = await call(job, "upload", ref=ref(p, "photograph"), file_id="file_notmine123")
        assert bad["ok"] is False                           # only files she gave for this job
        up = await call(job, "upload", ref=ref(p, "photograph"), file_id=photo_id, var="photo")
        assert up["ok"], up
        await call(job, "check", ref=ref(p, "I declare", "checkbox"))
        r = await call(job, "click", ref=ref(p, "Next", "button"))
        p = r["page"]
        assert "Verify with OTP" in p
        w = await call(job, "ask_owner", kind="otp", reason="Aadhaar wale mobile par aaya OTP bhariye", ref=ref(p, "Enter OTP"))
        assert w["status"] == "approved" and portal.STATE["last_otp"] not in json.dumps(w)
        r = await call(job, "click", ref=ref(w["page"], "Verify OTP", "button"))     # no approval needed for her own OTP
        p = r["page"]
        assert "Review and pay" in p and "XXXX XXXX 1234" in p
        pay = ref(p, "Pay", "button")
        assert "owner presses this" in re.search(rf"\[{pay}\][^\n]*", p).group(0)
        no = await call(job, "click", ref=pay)
        assert no["blocked"] == "payment"                   # Hoola never presses pay
        w = await call(job, "ask_owner", kind="payment", reason="₹107 fee aap khud pay kijiye", ref=pay)
        assert "kind" in w and w["status"] == "approved"
        p = await call(job, "page")
        ack = re.search(r"D49\d{9}", p)
        assert ack, p[:500]
        await call(job, "click", ref=ref(p, "Download acknowledgement", "link"))
        dl = (await call(job, "downloads"))["files"]
        assert dl and dl[-1]["name"].endswith(".pdf") and "file" not in dl[-1]
        trace = (await call(job, "trace"))["steps"]
        lit = [t["step"] for t in trace if t.get("action") == "fill" and (t.get("target") or {}).get("name") == "User ID"]
        var = [t["step"] for t in trace if (t.get("action") == "select" and "Title" in str(t.get("target"))) or t.get("radio")]
        saved = await call(job, "recipe_save", name="Demo portal Form D-49 application",
                           task="Apply for a new Form D-49 card on Demo Seva Portal", literal_steps=lit, variable_steps=var)
        assert saved["version"] == 1 and saved["owner_steps"] >= 5, saved
        await call(job, "site_note_add", site="127.0.0.1", note="Mobile must be 10 digits")
        await call(job, "finish", summary="Form D-49 jama ho gaya", proof=[f"Acknowledgement {ack.group(0)}"])
        out = await ops._wrap(job, "done", job.finished["summary"], job.finished)
    finally:
        stop.set()
        await who
        await op.close("main")
    return out, answered, ack.group(0)


def test_first_run_with_owner_then_learned(site):
    from app import chatfiles
    from app.operator import service as ops
    SEEN.clear()
    photo = chatfiles.store(T, "meghana.jpg", b"\xff\xd8\xff\xe0" + b"0" * 3000)["file_id"]

    async def go():
        try:
            return await _first_run(site, photo)
        finally:
            await ops.shutdown()
    out, answered, ack = asyncio.run(go())
    assert {"secret", "captcha", "otp", "payment"} <= set(answered)
    sub = portal.STATE["submissions"][-1]
    assert sub["first_name"] == "Meghana" and sub["mobile"] == "9890012345" and sub["dob"] == "1990-08-15"
    assert sub["state"] == "Maharashtra" and sub["aadhaar"] == AADHAAR and sub["photo"] == "meghana.jpg"   # she typed it
    assert out["status"] == "done" and ack in " ".join(out["proof"])
    assert out["outputs"] and out["outputs"][0]["file_id"] and out["outputs"][0]["name"].endswith(".pdf")
    assert out["recipe"] == "Demo portal Form D-49 application"
    # nothing secret ever reached the model, the recipe, the audit log or the job row
    seen = "\n".join(SEEN)
    for secret in (AADHAAR, PASSWORD, portal.STATE["last_otp"], portal.STATE["last_captcha"]):
        assert secret not in seen
    blob = ""
    for p in Path("data/operator").rglob("*"):
        if p.is_file() and p.suffix in (".json", ".jsonl", ".md"):
            blob += p.read_text(errors="ignore")
    for secret in (AADHAAR, PASSWORD, portal.STATE["last_otp"], "9890012345", "Meghana", "meghana@example.com"):
        assert secret not in blob, secret          # recipes, notes, playbooks and the audit log keep no personal values
    row = json.dumps(ops.get(T, out["id"]))       # the job keeps her request, never what she typed on the page
    for secret in (AADHAAR, PASSWORD, portal.STATE["last_otp"], "9890012345"):
        assert secret not in row, secret
    assert len(list(Path("data/operator").rglob("step_*.jpg"))) > 15      # audit trail with pictures
    from app.db import Message, session
    with session() as s:
        notes = [m.display or m.content for m in s.query(Message).filter(Message.role == "assistant").all()]
    assert any("Website ka kaam ho gaya" in (n or "") and ack in (n or "") for n in notes)


def _fake_brain(person_vars: dict, log: list):
    async def brain(system, history):
        log.append(history[-1])
        last = history[-1]["content"]
        res = {}
        if isinstance(last, list) and last and last[0].get("type") == "tool_result":
            try:
                res = json.loads(last[0]["content"])
            except (TypeError, ValueError):
                res = {"_text": last[0]["content"]}
        n = sum(1 for m in history if m["role"] == "assistant")
        if n == 0:
            return [{"type": "tool_use", "id": "t0", "name": "recipe_find", "input": {"query": "Form D-49 card"}}], "tool_use"
        if n == 1:
            name = res["recipes"][0]["name"]
            return [{"type": "tool_use", "id": "t1", "name": "recipe_run", "input": {"name": name, "variables": {}}}], "tool_use"
        if res.get("status") == "needs_input":
            return [{"type": "tool_use", "id": f"t{n}", "name": "recipe_run",
                     "input": {"name": "Demo portal Form D-49 application", "variables": person_vars}}], "tool_use"
        if res.get("status") == "needs_help":
            brain.helped = res["failed_step"]
            return [{"type": "tool_use", "id": f"t{n}", "name": "click", "input": {"ref": ref(res["page"], "Continue", "button")}}], "tool_use"
        if getattr(brain, "helped", None) is not None and "recipe_run" not in json.dumps(history[-2]["content"]):
            step, brain.helped = brain.helped, None
            return [{"type": "tool_use", "id": f"t{n}", "name": "recipe_run",
                     "input": {"name": "Demo portal Form D-49 application", "variables": person_vars, "start_step": step + 1}}], "tool_use"
        if res.get("status") == "done":
            m = re.search(r"D49\d{9}", res.get("page", ""))
            return [{"type": "tool_use", "id": f"t{n}", "name": "finish",
                     "input": {"summary": "Ho gaya", "proof": [m.group(0) if m else "?"]}}], "tool_use"
        return [{"type": "text", "text": f"Ruk gaya: {str(res)[:200]}"}], "end_turn"
    brain.helped = None
    return brain


def _replay(site, monkeypatch, person: dict, layout: str):
    from app.operator import service as ops
    portal.STATE["layout"] = layout
    log: list = []
    monkeypatch.setattr(ops, "_brain", _fake_brain(person["vars"], log))
    v = ops.start(T, "Form D-49 card apply karo, is baar " + person["vars"]["first_name"] + " ke liye", site + "/")

    async def go():
        stop, answered = asyncio.Event(), []
        who = asyncio.create_task(owner(person, stop, answered))
        try:
            out = await ops.run_job(v["id"])
        finally:
            stop.set()
            await who
            await ops.shutdown()
        return out, answered
    return asyncio.run(go()) + (log,)


PEOPLE = {
    "b": {"aadhaar": "999988887777", "vars": {"last_name": "Gawai", "first_name": "Sandesh", "dob": "02/01/1995",
          "father_name": "Ramesh Gawai", "email": "sandesh@example.com", "mobile": "9123456780", "address_line": "Shivaji Nagar",
          "area": "Old City", "city": "Akola", "pin_code": "444001", "title": "Shri", "gender": "Male"}},
    "c": {"aadhaar": "444455556666", "vars": {"last_name": "Nikhade", "first_name": "Ankita", "dob": "05/05/1998",
          "father_name": "Sunil Nikhade", "email": "ankita@example.com", "mobile": "9555566666", "address_line": "Ring Road",
          "area": "Gandhi Chowk", "city": "Nashik", "pin_code": "422001", "title": "Kumari", "gender": "Female"}},
}


def test_replay_jobs_survive_redesign_and_renamed_button(site, monkeypatch):
    from app import chatfiles
    from app.operator import service as ops
    photo = chatfiles.store(T, "meghana.jpg", b"\xff\xd8\xff\xe0" + b"0" * 3000)["file_id"]

    async def learn():
        try:
            return await _first_run(site, photo)
        finally:
            await ops.shutdown()
    asyncio.run(learn())
    ops._ops.clear()
    for layout in ("b", "c"):
        person = {**PEOPLE[layout], "vars": {**PEOPLE[layout]["vars"], "photo": photo}}
        out, answered, log = _replay(site, monkeypatch, person, layout)
        assert out["status"] == "done", (layout, out, log[-1])
        assert set(answered) <= {"secret", "captcha", "otp", "payment"} and "payment" in answered
        sub = portal.STATE["submissions"][-1]
        assert sub["first_name"] == person["vars"]["first_name"] and sub["aadhaar"] == person["aadhaar"]
        assert sub["mobile"] == person["vars"]["mobile"] and sub["title"] == person["vars"]["title"]
        assert out["outputs"] and out["outputs"][-1]["name"].endswith(".pdf")
        if layout == "c":     # "Next" became "Continue": the brain did that one step, then the recipe went on
            assert any("needs_help" in json.dumps(m.get("content", ""), default=str) for m in log)
    r = ops.recipes(T)[0]
    assert r["runs"] >= 2


def test_gates_need_her_tap_and_local_addresses_blocked(site):
    from app.operator import service as ops
    from app.operator.browser import OperatorError

    async def go():
        op = await ops.operator(T)
        v = ops.start(T, "Feedback form par 'bahut accha' bhejo", site + "/feedback")
        job = ops.Job(ops._row(v["id"]), op, ops.memory(T))
        stop, answered = asyncio.Event(), []
        try:
            r = await call(job, "open", url=site + "/feedback")
            p = r["page"]
            await call(job, "fill", ref=ref(p, "feedback"), value="bahut accha")
            assert (await call(job, "press", key="Enter", ref=ref(p, "feedback")))["blocked"] == "enter"
            send, delete = ref(p, "Send feedback"), ref(p, "Delete my account")
            assert (await call(job, "click", ref=send))["blocked"] == "needs_owner_approval"
            assert not portal.STATE.get("feedback")
            who = asyncio.create_task(owner({"aadhaar": ""}, stop, answered))
            w = await call(job, "ask_owner", kind="approve", reason="Feedback 'bahut accha' bhejun?", ref=send)
            assert w["status"] == "approved" and "approval_id" in w["next"]
            with pytest.raises(OperatorError):          # her yes was for "Send feedback", not for deleting the account
                await call(job, "click", ref=delete, approval_id=w["id"])
            r = await call(job, "click", ref=send, approval_id=w["id"])
            assert r["ok"] and "Feedback received" in await call(job, "page") and portal.STATE["feedback"] == ["bahut accha"]
            with pytest.raises(OperatorError):          # one yes = one click
                op._consume_approval(op.sessions["main"], w["id"], {"name": "Send feedback"})
            stop.set()
            await who
            # she says no -> nothing happens
            r = await call(job, "open", url=site + "/feedback")
            stop2, ans2 = asyncio.Event(), []
            who2 = asyncio.create_task(owner({"aadhaar": "", "approve": False}, stop2, ans2))
            w = await call(job, "ask_owner", kind="approve", reason="phir bhejun?", ref=ref(r["page"], "Send feedback"))
            assert w["status"] == "rejected" and "NO" in w["next"]
            stop2.set()
            await who2
            # a real local address (the VPS itself) is refused when private addresses aren't allowed
            op.allow_private = False
            with pytest.raises(OperatorError):
                await call(job, "open", url="http://127.0.0.1:8077/")
            with pytest.raises(OperatorError):
                await call(job, "open", url="file:///etc/passwd")
            op.allow_private = True
        finally:
            stop.set()
            await ops.shutdown()
    asyncio.run(go())


def test_job_rules_api_tool_and_employee(site):
    from fastapi.testclient import TestClient
    from app.agent.tools import HANDLERS, TOOLS, Ctx, ToolError
    from app.employee.roles import ROLES, duty_of, kind_of
    from app.operator import service as ops
    from app.voice import VOICE_TOOL_NAMES
    with pytest.raises(ops.OperatorJobError):
        ops.start(T, "x")
    with pytest.raises(ops.OperatorJobError):          # v0.75: never an OTP / PIN / card in the task text
        ops.start(T, "Form bharo, OTP 482913 hai", site)
    ctx = Ctx(tenant_id=T, conversation_id="c1")
    out = asyncio.run(HANDLERS["computer_operator"](ctx, action="start", task="Portal se bijli ka bill download karo",
                                                     start_url=site + "/"))
    assert out["status"] == "queued" and "Do not poll" in out["note_for_you"]
    with pytest.raises(ToolError):                      # one job at a time
        asyncio.run(HANDLERS["computer_operator"](ctx, action="start", task="Doosra kaam bhi karo abhi", start_url=site))
    st = asyncio.run(HANDLERS["computer_operator"](ctx, action="status"))
    assert st["id"] == out["task_id"] and st["status"] == "queued"
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    h = c.get("/api/operator").json()
    assert h["available"] and h["active"]["id"] == out["task_id"]
    assert c.post(f"/api/operator/tasks/{out['task_id']}/cancel").json()["status"] == "cancelled"
    assert c.post("/api/operator/requests/hxyz", json={"status": "approved", "answer": "1"}).status_code == 400
    assert c.get("/api/operator/frame").status_code == 404
    assert any(t["name"] == "computer_operator" for t in TOOLS) and "computer_operator" in VOICE_TOOL_NAMES
    assert duty_of("computer_operator") == "operator" and kind_of("computer_operator") == "action"
    assert "operator" in ROLES["computer_operator"]["duties"]
    from app.push import render
    t = render("operator_ask", {"status": "pending", "kind": "otp", "site": "x.gov.in", "reason": "OTP bhariye"}, "Santosh")
    assert t and "OTP" in t[0]
    # a restart closes the browser: running jobs stop honestly
    v = ops.start(T, "Status check karo portal par", site + "/")
    ops._set(v["id"], status="running")
    assert ops.resume_pending() == 1 and ops.get(T, v["id"])["status"] == "stopped"


def test_gate_words():
    from app.operator.browser import gate_of, is_secret_field
    btn = lambda n, **k: {"role": "button", "name": n, "tag": "button", "type": "submit", "inForm": True, **k}  # noqa: E731
    assert gate_of(btn("Pay ₹107 and Submit")) == "payment"
    assert gate_of(btn("Proceed to Pay")) == "payment"
    assert gate_of(btn("Final Submit")) == "commit" and gate_of(btn("Delete")) == "commit"
    assert gate_of(btn("Send OTP")) == "" and gate_of(btn("Verify OTP")) == "" and gate_of(btn("Login")) == ""
    assert gate_of(btn("Next")) == "" and gate_of(btn("Continue")) == "" and gate_of(btn("Search")) == ""
    assert gate_of({"role": "link", "name": "Download receipt", "tag": "a", "href": "/r.pdf"}) == ""
    box = lambda n, **k: {"role": "textbox", "name": n, "tag": "input", "type": "text", **k}  # noqa: E731
    from app.operator.browser import field_kind
    assert is_secret_field(box("Enter OTP")) and is_secret_field(box("x", type="password"))
    assert not is_secret_field(box("Aadhaar number")) and field_kind(box("Aadhaar number")) == "id"   # v0.75 from the locker
    assert is_secret_field(box("Card number")) and is_secret_field(box("Account number", sensitive=True))
    assert not is_secret_field(box("PIN code", nameAttr="pin", id="pin", sensitive=True)) and not is_secret_field(box("Mobile number"), "9890012345")
    assert is_secret_field(box("Reference"), "4111 1111 1111 1111")       # a card number typed into any box
