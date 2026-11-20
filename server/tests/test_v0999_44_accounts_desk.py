"""v0.999.44 ACCOUNTS DESK (built as 0.999.43) - the GST & Accounts employee's own section (the SEO / Social desks' twin): its chat (kind
'accounts', out of her Hoola chats, files / photos / documents can be attached) beside the desk's screens (bahi.js, grouped
into six pages); a turn in that chat (or a call from it) knows the desk and has the accounts desk tool in view; the tool
reads an attached bill into a DRAFT, fixes a draft, imports a statement, prepares returns inside Hoola - never adds to the
register, sends to the GST portal, files, records TDS, closes a month or pays; the phone calls it on that chat."""
import asyncio
import os
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0845_bahi_a6 import GOOD, MINE, _valid_gstin

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
T = "default"


@pytest.fixture
def acc(env, monkeypatch):
    from app.bahi import connect
    from app.employee import hire
    sup = _valid_gstin("27AABCA1234B1Z")
    monkeypatch.setattr(connect, "supplier_check", lambda tenant, g, filing=True: {"status": "active", "source": "API Setu (GSTN)", "notes": []})
    monkeypatch.setattr(connect, "status", lambda tenant: [{"gstin": MINE, "connected": True}])
    hire.hire(T, "accounts", trust="saathi")
    yield sup


def bill(sup):
    return GOOD.format(sup=sup, mine=MINE)


def test_the_accounts_chat_is_its_own_and_knows_the_desk(acc):
    from app.main import app
    from app import accountschat, convs
    with TestClient(app) as c:
        r = c.get("/api/accounts/chat").json()
        assert r["id"]
        home = c.post("/api/conversations").json()["id"]
        aid = c.post("/api/accounts/chat/new").json()["id"]      # the untouched first chat is reused
        assert aid == r["id"]
        ids = [x["id"] for x in c.get("/api/conversations").json()["conversations"]]
        assert home in ids and aid not in ids                    # never in her Hoola chat list
        assert accountschat.is_accounts(aid) and not accountschat.is_accounts(home)
        assert c.get(f"/api/accounts/chat/{aid}/ok").json()["ok"] and c.get(f"/api/accounts/chat/{home}/ok").status_code == 404
        convs.mark(T, aid, "message")
        assert convs.current(T) != aid
        d = c.get("/api/accounts/desk").json()
        assert d["hired"] and d["gstins"] == [MINE] and d["trust"] == "Partner" and "dues" in d
    b = accountschat.block(T)
    assert "<accounts_desk>" in b and MINE in b and "can NOT add a bill to the register" in b and "never invent a figure" in b
    assert "Never ask for her GST portal password or an OTP" in b and "file_id" in b
    assert "Attach a bill" in accountschat.greeting(T)


def test_a_call_from_the_accounts_chat_is_an_accounts_turn(acc):
    from app import accountschat, callconv
    from app.db import Conversation, session
    aid = accountschat.current(T)["id"]
    with session() as s:
        c = Conversation(tenant_id=T, kind="call", origin_conv=aid)
        s.add(c)
        s.flush()
        call = c.id
    assert callconv.origin_of(call) == aid and accountschat.is_accounts(call)


def test_the_tool_reads_a_bill_into_a_draft_and_never_puts_it_in_the_register(acc):
    from app.agent.accountsdesk_tools import accounts_desk
    from app.agent.tools import Ctx, ToolError
    from app.bahi import register as REG
    sup = acc
    run = lambda ctx=None, **a: asyncio.run(accounts_desk(ctx or Ctx(T, "c1"), **a))   # noqa: E731
    r = run(action="read_bill", text=bill(sup))
    assert r["status"] == "draft" and r["fields"]["total"] == 11800.0 and "NOT in the register" in r["note"]
    assert not REG.listing(T)                                    # nothing in the register yet
    f = run(action="fix_bill", bill_id=r["id"], changes={"total": "11900"})
    assert f["before"] == {"total": 11800.0} and f["after"] == {"total": 11900.0} and f["status"] == "draft"
    assert any("difference" in c["text"] for c in f["checks"])  # the checks ran again
    assert run(action="read", what="bills")["bills"][0]["id"] == r["id"]
    s = run(action="read")
    assert s["bills_to_check"] == 1 and s["gstins"] == [MINE]
    with pytest.raises(ToolError):
        run(action="confirm_bill", bill_id=r["id"])              # it can never add a bill to the register
    with pytest.raises(ToolError):
        run(action="file", form="gstr1")                         # nor file, save to the portal, record TDS or pay
    with pytest.raises(ToolError):
        run(Ctx(T, "c1", actor="customer:x"), action="read_bill", text=bill(sup))
    from app.agent.tools import TOOLS
    spec = [t for t in TOOLS if t["name"] == "accounts_desk"][0]
    assert set(spec["input_schema"]["properties"]["action"]["enum"]) == {"read", "read_bill", "fix_bill", "import_statement",
                                                                        "match_bank", "prepare", "tds", "supplier"}


def test_a_bill_attached_in_the_chat_is_read_by_its_file_id(acc):
    from app import chatfiles
    from app.agent.accountsdesk_tools import accounts_desk
    from app.agent.tools import Ctx
    m = chatfiles.store(T, "acme-bill.txt", bill(acc).encode(), "text/plain")
    ctx_line = chatfiles.context(T, [m["file_id"]])
    assert m["file_id"] in ctx_line                               # the model is told the file_id of what she attached
    r = asyncio.run(accounts_desk(Ctx(T, "c1"), action="read_bill", file_id=m["file_id"]))
    assert r["status"] == "draft" and r["channel"] == "chat" and r["fields"]["number"] == "ACM/26/0042"


def test_not_hired_is_refused(env):
    from app.agent.accountsdesk_tools import accounts_desk
    from app.agent.tools import Ctx, ToolError
    with pytest.raises(ToolError):
        asyncio.run(accounts_desk(Ctx(T, "c1"), action="read"))


def test_turn_hooks_and_admission():
    src = (ROOT / "server/app/agent/santosh.py").read_text()
    assert "_accc.is_accounts(conversation_id)" in src and "_accc.block" in src and "adm.admit_families(_accc.FAMILIES)" in src
    from app import accountschat
    from app.agent import admit
    assert set(accountschat.FAMILIES) <= set(admit.FAMILY_OF.values())
    assert admit.FAMILY_OF["accounts_desk"] == "accountsdesk"
    assert '"accounts")' in (ROOT / "server/app/callconv.py").read_text() and '"accounts")' in (ROOT / "server/app/convs.py").read_text()


def test_page_and_wiring():
    from app.main import app, APP_VERSION
    c = TestClient(app)
    r = c.get("/console/accounts")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "accountsdesk.js" in r.text
    html = (CON / "accountsdesk.html").read_text()
    for f in ("chatkit.js", "quality.js", "md.js", "mark.js", "stream.js", "bahi.js", "seodesk.css", "accountsdesk.css", "accountsdesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    js = (CON / "accountsdesk.js").read_text()
    for need in ("/api/accounts/chat", "/api/accounts/desk", "HoolaChat.mount", "plus: true", "quality: true", "/files`", "files,",
                 "hoola.accounts.side", "HoolaBahi(", "bare: true", "dragover", "paste"):
        assert need in js, need
    for tab in ("today", "bills", "returns", "bank", "close", "settings"):
        assert f"['{tab}'," in js
    bj = (CON / "bahi.js").read_text()
    assert "bare, ask" in bj and "show: keys =>" in bj
    assert "location.assign('/console/accounts')" in (CON / "v2.js").read_text()
    css = (CON / "accountsdesk.css").read_text()
    assert "#app .ddk" in css and "--pri:var(--acc)" in css


def test_phone_calls_the_accounts_employee():
    es = (ROOT / "lib/ui/employees_screen.dart").read_text()
    assert "callAccountsDesk" in es and "app.api!.accountsChat()" in es
    he = (ROOT / "lib/ui/shell/hoola_employees.dart").read_text()
    assert "callAccountsDesk(context, staff.app)" in he and "'/console/accounts'" in he
    assert "accountsChat()" in (ROOT / "lib/api.dart").read_text()


# ---------------------------------------------------------------- the page in a real browser
@pytest.fixture
def acc_server(acc, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY, acc
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_accounts_desk_in_a_real_browser(acc_server, tmp_path):
    base, browser, key, sup = acc_server
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    f = tmp_path / "acme-bill.txt"
    f.write_text(bill(sup))
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/accounts")
        pg.wait_for_selector("#sdTabs [data-tab='today']", timeout=20000)
        try:
            pg.wait_for_function("() => document.querySelector('#sdThread').innerText.includes('Attach a bill')", timeout=20000)
        except Exception:
            raise AssertionError(f"chat empty: errors={errors} page={pg.inner_text('body')[:600]!r}")
        pg.wait_for_selector("#adBahi .acd-tabs", timeout=20000)
        assert "Needs you" in pg.inner_text("#adNeeds")
        pg.evaluate("document.querySelector('#sdChat').__keep = 1")
        for tab, want in (("bills", ["Bills", "Register"]), ("returns", ["Credit (ITC)", "GSTR-1", "GSTR-3B", "e-Invoice"]),
                          ("bank", ["Bank", "Pay + TDS"]), ("close", ["Month-end", "CA pack"]), ("settings", ["Connection", "Rules", "Plan"]),
                          ("today", ["Overview"])):
            pg.click(f"#sdTabs [data-tab='{tab}']")
            pg.wait_for_function("(w) => { const t = [...document.querySelectorAll('#adBahi [data-a=tab]')].map(b => b.textContent); return w.every(x => t.includes(x)) && t.length === w.length; }", arg=want, timeout=10000)
            assert pg.evaluate("document.querySelector('#sdChat').__keep") == 1     # the chat stayed while the page changed
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        if width == 1440 and scheme == "light":
            pg.set_input_files("#adPick", str(f))                       # + in the chat: the file is uploaded to this chat
            pg.wait_for_function("() => { const x = document.querySelector('#adFiles .ac-file'); return x && !x.classList.contains('up') && !x.classList.contains('bad'); }", timeout=15000)
            assert "acme-bill.txt" in pg.inner_text("#adFiles")
            pg.click("#adFiles .ac-file button")                        # and taken back out with its x
            assert pg.evaluate("document.querySelector('#adFiles').hidden")
            pg.click("#sdTabs [data-tab='settings']")
            pg.wait_for_selector("#adEmp [data-trust]")
            pg.click("#sdSwap")
            assert pg.evaluate("document.querySelector('#sdBody').classList.contains('right')")
            pg.click("#sdSwap")
            pg.click("#sdFold")
            assert pg.evaluate("document.querySelector('#sdChat').classList.contains('folded')")
            pg.click("#sdFold")
        if shots:
            Path(shots).mkdir(parents=True, exist_ok=True)
            for tab in ("today", "bills", "returns", "bank", "close", "settings"):
                pg.click(f"#sdTabs [data-tab='{tab}']")
                time.sleep(0.6)
                pg.screenshot(path=f"{shots}/accountsdesk_{tab}_{scheme}_{width}.png", full_page=False)
        ctx.close()
    assert not errors, errors
