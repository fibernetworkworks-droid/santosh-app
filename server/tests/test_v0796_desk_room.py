"""v0.796 DESK ROOM: a web-console desk for every live AI employee (owner, 11 Nov: "LOT OF EMPLOYEE HAS BEEN DEVELOPED
IN APP BUT IT IS NOT AVAILABLE IN WEB CONSOLE CHECK THIS FIRST THEN CATEGORY WISE DEVELOP AND DESIGN IT IN CONSOLE").

The audit found 31 live employees - Finance & Banking 3, Retail & E-commerce 3, Health Insurance 3, Kaan, Construction &
Real Estate 21 - whose "Open desk" pointed at a console view that did not exist. Four department desks now read each
employee's OWN tool into forms and run it through the same dispatch the chat uses; Kaan's desk is Hoola Flow."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
EMP = (CON / "employees.js").read_text(encoding="utf-8")
V2 = (CON / "v2.js").read_text(encoding="utf-8")
HTML = (CON / "v2.html").read_text(encoding="utf-8")
CSS = (CON / "v2.css").read_text(encoding="utf-8")
DDK = (CON / "deptdesk.js").read_text(encoding="utf-8")


def _desks():
    body = re.search(r"const DESKS = \{(.*?)\};", EMP, re.S).group(1)
    m = dict(re.findall(r"(\w+): '(\w+)'", body))
    loop = re.search(r"for \(const k of \[(.*?)\]\) DESKS\[k\] = '(\w+)'", EMP, re.S)
    for k in re.findall(r"'(\w+)'", loop.group(1)):
        m[k] = loop.group(2)
    return m


# ---------------------------------------------------------------- the audit, held for ever
def test_every_live_employee_opens_a_real_desk():
    """The bug: a live employee whose desk view does not exist (Open desk did nothing)."""
    from app.employee import hire
    views = set(re.findall(r'id="v-(\w+)"', HTML)) | {"flow"}           # flow = its own page (/console/flow)
    desks = _desks()
    missing = [k for k, c in hire.CATALOG.items() if c.get("live") and desks.get(k, k + "desk") not in views]
    assert not missing, missing
    assert desks["kaan"] == "flow"
    assert "if (v === 'flow') { location.assign('/console/flow'" in V2


def test_desk_room_covers_the_four_departments():
    from app.employee import deskroom as D, hire as H
    groups = {d["group"]: {k for ln in d["lanes"] for k in ln["keys"]} for d in D.DEPTS}
    for g in (H.FIN_GROUP, H.RETAIL_GROUP, H.HEALTHINS_GROUP, H.CONST_GROUP):
        live = {k for k, c in H.CATALOG.items() if c.get("group") == g and c.get("live")}
        assert groups[g] == live, (g, live ^ groups[g])                 # every live seat, none twice
    assert len(D.keys()) == len(set(D.keys())) == 30
    for k in D.keys():
        assert D.tools_of(k) and D.tools_of(k)[0] == k, k                # its own tool first


def test_every_action_becomes_a_form_from_the_full_description():
    from app.employee import deskroom as D
    total = guessed = 0
    for k in D.keys():
        for t in D.tools_of(k):
            s = D.spec(t)
            assert s["actions"], t
            for a in s["actions"]:
                total += 1
                guessed += a["guessed"]
                for f in a["fields"]:
                    assert f["name"] != s["param"] and f["label"], (t, a["id"])
    assert total > 400 and guessed / total < 0.05, (total, guessed)
    # the registry copy is cut at 1,200 chars for the model; the desk reads the module's full text
    comp = next(a for a in D.spec("paisa_sahayak")["actions"] if a["id"] == "complaint")
    assert not comp["guessed"] and {"bank", "txn_ref", "narrative"} <= {f["name"] for f in comp["fields"]}
    pay = next(a for a in D.spec("bima_desk")["actions"] if a["id"] == "payable")
    items = next(f for f in pay["fields"] if f["name"] == "items")
    assert items["shape"] == "rows" and items["cols"] == ["name", "billed", "payable_cap"]
    assert "room-rent" in pay["gives"]
    ck = next(a for a in D.spec("bima_desk")["actions"] if a["id"] == "claim_checklist")
    assert next(f for f in ck["fields"] if f["name"] == "claim_type")["options"] == ["cashless", "reimbursement"]
    rd = D.spec("const_store_dekho")
    assert rd["read"] and rd["param"] == "what" and [a["id"] for a in rd["actions"]] == ["stock", "reconcile"]
    done = next(a for a in D.spec("const_meet")["actions"] if a["id"] == "action_done")
    assert [f["name"] for f in done["fields"]] == ["action_id"]         # "action (id)" when the field is action_id
    assert D.human("tds_reconcile") == "TDS reconcile" and D.human("copay_pct") == "Copay %" and D.human("ncr") == "NCR"


# ---------------------------------------------------------------- the routes
def test_routes_hire_gate_and_real_runs(env):
    from app.main import app
    c = TestClient(app)
    ov = c.get("/api/deskroom").json()
    assert [d["id"] for d in ov["depts"]] == ["fin", "retail", "healthins", "const"]
    assert ov["where"]["const_bim"] == "const" and ov["elsewhere"] == {"kaan": "flow"}
    assert c.get("/api/deskroom/nope").status_code == 404
    run = lambda k, t, a, args=None: c.post(f"/api/deskroom/{k}/run", json={"tool": t, "action": a, "args": args or {}})
    r = run("paisa_sahayak", "paisa_sahayak", "loan", {"amount": 500000, "rate": 12, "months": 36})
    assert r.status_code == 400 and "Hire" in r.json()["detail"]        # the desk opens once it is hired
    assert c.post("/api/employees/paisa_sahayak/hire", json={"trust": "seekh"}).status_code == 200
    r = run("paisa_sahayak", "paisa_sahayak", "loan", {"amount": 500000, "rate": 12, "months": 36, "fee_pct": 2, "junk": 1})
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert res["emi"] == 16607.15 and res["money_received"] == 488200.0 and res["apr_effective_pct"] > 12
    assert run("paisa_sahayak", "paisa_sahayak", "nope").status_code == 400
    assert run("paisa_sahayak", "const_store", "lot").status_code == 400            # never another employee's tool
    # a complaint never takes a full account number: last four only
    r = run("paisa_sahayak", "paisa_sahayak", "complaint", {"issue_type": "charges", "bank": "Test Bank", "account": "123456789012"})
    assert r.status_code == 200 and "123456789012" not in r.text and "9012" in r.text
    d = c.get("/api/deskroom/fin").json()
    pe = next(e for ln in d["lanes"] for e in ln["employees"] if e["key"] == "paisa_sahayak")
    assert pe["status"] == "hired" and pe["tools"][0]["tool"] == "paisa_sahayak" and d["conversation_id"]
    # Construction: a store record written on the desk is there when the desk reads it back
    assert c.post("/api/employees/const_store/hire", json={"trust": "seekh"}).status_code == 200
    assert run("const_store", "const_store", "lot", {"item": "Cement OPC 53", "unit": "bag", "min_qty": 50}).status_code == 200
    assert run("const_store", "const_store", "grn", {"item": "Cement OPC 53", "qty": 200, "rate": 380, "vendor": "ABC",
                                                      "invoice_no": "C-1"}).status_code == 200
    st = run("const_store", "const_store_dekho", "stock").json()["result"]
    assert st["lots"][0]["balance"] == 200.0
    # paused: the desk says so and runs nothing
    assert c.post("/api/employees/const_store/pause").status_code == 200
    r = run("const_store", "const_store_dekho", "stock")
    assert r.status_code == 400 and "paused" in r.json()["detail"].lower()


def test_runs_through_the_chat_dispatch_as_the_owner():
    src = (ROOT / "server" / "app" / "employee" / "deskroom.py").read_text(encoding="utf-8")
    assert "dispatch(tool, clean, ctx)" in src and 'actor="owner"' in src and "scrub(out)" in src
    main = (ROOT / "server" / "app" / "main.py").read_text(encoding="utf-8")
    assert "app.include_router(_deskroom_router(require_key, current_tenant))" in main


# ---------------------------------------------------------------- the console
def test_console_wiring():
    assert '<section class="view" id="v-deptdesk"' in HTML and "/static/console/deptdesk.js?v=" in HTML
    assert "HoolaDeptDesk({api, esc, toast" in V2 and "if (v === 'deptdesk') DDK?.open($('#deptdesk'), arg);" in V2
    assert "openView(v, v === 'systems' || v === 'deptdesk' ? key : '')" in EMP
    assert "esc(" in DDK and "innerHTML = `" in DDK
    for c in (".live", ".top", ".tag"):                                # console-wide class names never reused
        assert f'class="{c[1:]}' not in DDK and f" {c[1:]}\"" not in DDK
    assert "/api/deskroom/${encodeURIComponent(e.key)}/run" in DDK


def test_css_is_crisp_and_on_one_scale():
    a = CSS.index("/* v0.796 DESK ROOM")
    blk = CSS[a:]
    assert "backdrop-filter" not in blk and "font-weight:700" not in blk and "text-transform:uppercase" not in blk
    sizes = {float(x) for x in re.findall(r"font(?:-size)?:[^;{}]*?(\d+(?:\.\d+)?)px", blk)}
    assert min(sizes) >= 11.5, sorted(sizes)
    for line in blk.splitlines():
        if "animation:ddkUp" in line or "animation:ddkDraw" in line:
            assert "backwards" in line, line
    assert blk.count("infinite") == 1                                  # only the running dot loops
    assert not re.search(r"#[0-9a-fA-F]{6}", blk)                        # tokens only: light / dark follow


def _walk(browser, base, key, width, height, scheme):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme)
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/")
    pg.wait_for_selector("#composer")
    pg.evaluate("document.querySelector('.sn[data-v=\"hire\"]')?.click()")
    pg.wait_for_selector("[data-ae=dept]")
    pg.locator("[data-ae=dept][data-id=fin]").first.click()
    pg.locator("[data-ae=role][data-key=paisa_sahayak]").first.click()
    pg.locator("[data-ae=open][data-key=paisa_sahayak]").first.click()
    pg.wait_for_selector(".ddk-hero")
    assert pg.locator(".ddk-h1").text_content() == "Finance & Banking"
    assert pg.locator(".ddk-emp").count() == 3 and pg.locator(".ddk-dept").count() == 4
    assert pg.locator(".ddk-emp[aria-current=true] .ddk-empname").text_content().startswith("Paisa Sahayak")
    pg.locator(".ddk-act[data-a=loan]").click()
    pg.fill("#ddkf-amount", "500000")
    pg.fill("#ddkf-rate", "12")
    pg.fill("#ddkf-months", "36")
    pg.locator("[data-dd=run]").click()
    pg.wait_for_selector(".ddk-res .ddk-tile")
    shots = __import__("os").environ.get("CONSOLE_SHOTS")
    if shots:
        pg.screenshot(path=f"{shots}/ddk-fin-{width}-{scheme}.png", full_page=True)
    out = pg.locator(".ddk-res").text_content()
    assert "16,607.15" in out and "EMI" in out
    # a list-of-rows field draws as a small table editor
    pg.locator(".ddk-act[data-a=compare]").click()
    assert pg.locator(".ddk-form [data-rows=offers]").count() in (0, 1)
    # Construction: five lanes, the not-hired desk explains itself and offers Hire
    pg.locator(".ddk-dept[data-id=const]").click()
    pg.wait_for_selector(".ddk-lane")
    assert pg.locator(".ddk-lane").count() == 5 and pg.locator(".ddk-emp").count() == 21
    if shots:
        pg.screenshot(path=f"{shots}/ddk-const-{width}-{scheme}.png", full_page=True)
    assert pg.locator("[data-dd=hire]").count() == 1 and "It will never" in pg.locator(".ddk-main").text_content()
    assert pg.evaluate("document.querySelector('.ddk').scrollWidth <= document.querySelector('.ddk').clientWidth + 1")
    assert not errs, errs
    ctx.close()


def test_the_desk_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    from app.employee import hire
    hire.hire("default", "paisa_sahayak", "seekh")
    _walk(browser, base, key, 1280, 900, "light")
    _walk(browser, base, key, 390, 844, "dark")
