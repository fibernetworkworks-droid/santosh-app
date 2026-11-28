"""MAINFRAME DESK: the Mainframe Modernization Architect's own section, built like the finance desks - its own chat (kind
'mainframe') with the desk block + the mainframe tool in view; COBOL programs read (paragraphs never reached, calls, DB2, CICS, files,
risks); copybooks laid out and a record decoded from EBCDIC / packed / zoned bytes; JCL (the real program under IKJEFT01, datasets,
rerun risks); an inventory mapped into waves, cycles and shared tables; a translation proved side by side (rounding, sign, case, order);
the CI workflow is valid YAML and its compare step really fails a changed output; walked in a browser."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"

COBOL = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYCALC.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT EMP-FILE ASSIGN TO EMPIN.
           SELECT OUT-FILE ASSIGN TO PAYOUT
               FILE STATUS IS WS-OUT-ST.
       DATA DIVISION.
       FILE SECTION.
       FD  EMP-FILE.
       01  EMP-REC.
           05  EMP-ID         PIC X(6).
           05  EMP-RATE       PIC S9(5)V99 COMP-3.
           05  EMP-HOURS      PIC 9(3)V9.
       WORKING-STORAGE SECTION.
       01  WS-OUT-ST          PIC XX.
       01  WS-PAY             PIC S9(7)V99 COMP-3.
       01  WS-YY              PIC 99.
       01  WS-PGM             PIC X(8) VALUE 'TAXCALC'.
           COPY PAYCONST.
       PROCEDURE DIVISION.
       0000-MAIN.
           PERFORM 1000-INIT
           PERFORM 2000-PROCESS UNTIL WS-EOF
           PERFORM 9000-END
           STOP RUN.
       1000-INIT.
           OPEN INPUT EMP-FILE.
       2000-PROCESS.
           READ EMP-FILE AT END SET WS-EOF TO TRUE END-READ
           IF EMP-HOURS > 40
              COMPUTE WS-PAY = EMP-RATE * 40 + EMP-RATE * 1.5 * (EMP-HOURS - 40)
           ELSE
              COMPUTE WS-PAY ROUNDED = EMP-RATE * EMP-HOURS
           END-IF
           CALL 'TAXCALC' USING WS-PAY
           CALL WS-PGM USING WS-PAY
           EXEC SQL
              SELECT RATE INTO :WS-RATE FROM PAYROLL.TAXRATES WHERE ID = :EMP-ID
           END-EXEC
           GO TO 2000-EXIT.
       2000-EXIT.
           EXIT.
       8000-OLD-REPORT.
           DISPLAY 'NEVER'.
       9000-END.
           CLOSE EMP-FILE.
"""
JCL = """//PAYJOB   JOB (ACCT),'PAYROLL',CLASS=A,MSGCLASS=X
//* nightly payroll
//STEP010  EXEC PGM=IEFBR14
//DEL1     DD DSN=PAY.WORK.SORTED,DISP=(MOD,DELETE,DELETE),
//            SPACE=(TRK,1)
//STEP020  EXEC PGM=SORT
//SORTIN   DD DSN=PAY.EMP.MASTER,DISP=SHR
//SORTOUT  DD DSN=PAY.WORK.SORTED,DISP=(NEW,CATLG),
//            SPACE=(CYL,(5,5))
//SYSIN    DD *
  SORT FIELDS=(1,6,CH,A)
/*
//STEP030  EXEC PGM=IKJEFT01,COND=(4,LT)
//EMPIN    DD DSN=PAY.WORK.SORTED,DISP=SHR
//PAYOUT   DD DSN=PAY.OUT(+1),DISP=(NEW,CATLG,DELETE)
//SYSTSIN  DD *
  DSN SYSTEM(DB2P)
  RUN PROGRAM(PAYCALC) PLAN(PAYPLAN)
  END
/*
//STEP040  EXEC PAYRPT
"""
CPY = """       01  CUSTOMER-REC.
           05  CUST-ID            PIC X(8).
           05  CUST-NAME          PIC X(20).
           05  CUST-BAL           PIC S9(7)V99 COMP-3.
           05  CUST-YY            PIC 99.
           05  CUST-ITEMS         PIC 9(4) COMP.
           05  CUST-STATUS        PIC X.
               88  ACTIVE         VALUE 'A'.
           05  CUST-AMT-ALT REDEFINES CUST-BAL PIC X(5).
           05  CUST-HIST OCCURS 3 TIMES.
               10  H-DATE         PIC 9(8).
               10  H-AMT          PIC S9(5)V99.
"""
REC = ("C0000001".encode("cp037") + "ANNA SMITH".ljust(20).encode("cp037") + bytes.fromhex("000012345C") + "26".encode("cp037")
       + (7).to_bytes(2, "big") + "A".encode("cp037") + b"".join("20260101".encode("cp037") + "000123".encode("cp037") + bytes([0xD4]) for _ in range(3))).hex()
OUT = """       01 OUT-REC.
          05 O-ID   PIC X(6).
          05 O-NAME PIC X(10).
          05 O-PAY  PIC S9(5)V99.
"""
NM = lambda s: s.ljust(10)   # noqa: E731
OLD = ["A00001" + NM("ANNA") + "000123E", "A00002" + NM("BEN") + "000200{", "A00003" + NM("CARL") + "000050A", "A00004" + NM("DORA") + "000010{"]
NEW = ["A00001" + NM("ANNA") + "000123F", "A00002" + NM("BEN") + "000200}", "A00003" + NM("carl") + "000050A", "A00005" + NM("EVE") + "000001A"]
PROOF = "## old\n" + "\n".join(OLD) + "\n## new\n" + "\n".join(NEW) + "\n"
SAME = "## old\n" + "\n".join(OLD) + "\n## new\n" + "\n".join(OLD) + "\n"
TAX = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. TAXCALC.
       PROCEDURE DIVISION.
       MAIN-PARA.
           EXEC SQL UPDATE PAYROLL.TAXRATES SET USED = 1 END-EXEC
           CALL 'ROUNDIT'
           GOBACK.
"""
RND = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. ROUNDIT.
       PROCEDURE DIVISION.
       A.
           CALL 'TAXCALC'
           GOBACK.
"""
OLDRPT = "       IDENTIFICATION DIVISION.\n       PROGRAM-ID. OLDRPT.\n       PROCEDURE DIVISION.\n       A.\n           ALTER B TO PROCEED TO C.\n           STOP RUN.\n"
INV = (f"## PAYCALC.cbl\n{COBOL}\n## TAXCALC.cbl\n{TAX}\n## ROUNDIT.cbl\n{RND}\n## OLDRPT.cbl\n{OLDRPT}\n## PAYCONST\n       01 PAY-CONST PIC 9(3) VALUE 40.\n## PAYJOB.jcl\n{JCL}")


@pytest.fixture
def mfc(env):
    from app import mainframechat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "mainframe_arch", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_program_layout_and_jcl():
    from app.mfdesk import cobol as C, jcl as J, layout as L
    p = C.analyse(COBOL)["programs"][0]
    assert p["name"] == "PAYCALC" and p["dead"] == ["8000-OLD-REPORT"] and p["tables"] == ["PAYROLL.TAXRATES"] and p["copies"] == ["PAYCONST"]
    assert {"to": "TAXCALC", "how": "static"} in p["calls"] and any(c["how"] == "dynamic" and c["values"] == ["TAXCALC"] for c in p["calls"])
    assert [f["name"] for f in p["files"]] == ["EMP-FILE", "OUT-FILE"] and p["files"][0]["status"] == "" and p["files"][1]["status"] == "WS-OUT-ST"
    t = " ".join(i["text"] for i in C.analyse(COBOL)["issues"])
    assert "EMP-FILE has no FILE STATUS" in t and "COMPUTE without ROUNDED" in t and "two-digit year" in t and "never reached" in t.lower() or "no PERFORM" in t
    free = C.analyse("IDENTIFICATION DIVISION.\nPROGRAM-ID. FREE1.\nPROCEDURE DIVISION.\nMAIN.\n  *> a comment\n  PERFORM WORK\n  GOBACK.\nWORK.\n  ALTER X TO PROCEED TO Y.\n")
    assert free["programs"][0]["name"] == "FREE1" and free["counts"]["bad"] == 1 and free["programs"][0]["dead"] == []
    two = C.analyse(COBOL + TAX)
    assert [x["name"] for x in two["programs"]] == ["PAYCALC", "TAXCALC"]
    with pytest.raises(C.CobolError):
        C.analyse("hello")
    r = L.analyse(CPY, "cp037", REC)
    rows = {x["name"]: x for x in r["rows"]}
    assert r["length"] == 83 and rows["CUST-BAL"]["offset"] == 28 and rows["CUST-BAL"]["length"] == 5 and rows["CUST-ITEMS"]["length"] == 2
    assert rows["CUST-AMT-ALT"]["offset"] == 28 and rows["H-AMT"]["offset"] == 46 and rows["CUST-STATUS"]["conds"][0]["name"] == "ACTIVE"
    assert rows["CUST-BAL"]["type"]["java"] == "BigDecimal" and rows["CUST-BAL"]["type"]["sql"] == "DECIMAL(9,2)" and rows["CUST-ITEMS"]["type"]["sql"] == "SMALLINT"
    vals = {f["name"]: f["value"] for f in r["decoded"]["fields"]}
    assert vals["CUST-BAL"] == "123.45" and vals["CUST-ITEMS"] == 7 and vals["H-AMT"] == "-12.34" and vals["CUST-ID"] == "C0000001"
    assert "h: OCCURS" not in r["ddl"] and "cust_hist: OCCURS 3" in r["ddl"] and "h_date" not in r["ddl"] and "cust_bal DECIMAL(9,2)" in r["ddl"]
    assert "public record CustomerRec(" in r["java"] and any("two-digit year" in i["text"] for i in r["issues"])
    ns: dict = {}
    exec(compile(r["python"], "decode.py", "exec"), ns)   # the generated decoder decodes the same record
    got = ns["decode_customer_rec"](bytes.fromhex(REC))
    assert str(got["cust_bal"]) == "123.45" and str(got["h_amt"]) == "-12.34" and got["cust_items"] == 7
    bad = L.decode(REC[:56] + "FFFFFFFFFF" + REC[66:], [dict(x) for x in r["rows"]], "cp037")
    assert any("not valid packed decimal" in (f["bad"] or "") for f in bad["fields"])
    assert L.analyse("01 A.\n  05 B PIC S9(9) COMP.\n  05 C PIC S9(10) COMP-3.\n  05 D COMP-2.\n")["length"] == 4 + 6 + 8
    with pytest.raises(L.LayoutError):
        L.analyse("nothing")
    j = J.analyse(JCL)
    steps = {s["step"]: s for s in j["steps"]}
    assert j["programs"] == ["PAYCALC"] and steps["STEP030"]["program"] == "PAYCALC" and steps["STEP030"]["plan"] == "PAYPLAN"
    assert steps["STEP020"]["sort"] == ["SORT FIELDS=(1,6,CH,A)"] and steps["STEP010"]["deletes"] == ["PAY.WORK.SORTED"] and steps["STEP010"]["writes"] == []
    assert j["gdgs"] == ["PAY.OUT"] and j["flows"] == [{"dsn": "PAY.WORK.SORTED", "from": "PAYJOB.STEP020", "to": "PAYJOB.STEP030"}]
    assert any("rerun stops" in i["text"] for i in j["issues"]) and any("procedure PAYRPT" in i["text"] for i in j["issues"])
    with pytest.raises(J.JclError):
        J.analyse("not jcl")


def test_inventory_proof_and_ci(tmp_path):
    from app.mfdesk import ci as CI, inventory as I, layout as L, proof as P
    r = I.analyse(INV)
    progs = {p["name"]: p for p in r["programs"]}
    assert r["totals"]["programs"] == 4 and r["copybooks"] == ["PAYCONST"] and r["cycles"] == [["ROUNDIT", "TAXCALC"]]
    assert r["waves"] == [{"wave": 1, "programs": ["OLDRPT", "ROUNDIT", "TAXCALC"]}, {"wave": 2, "programs": ["PAYCALC"]}]
    assert r["missing"] == {"program": [], "copybook": [], "proc": ["PAYRPT"]} and progs["PAYCALC"]["started_by"] == ["PAYJOB.STEP030"]
    assert progs["OLDRPT"]["approach"] == "Retire?" and progs["PAYCALC"]["approach"] == "Translate (batch + DB2)"
    assert r["table_groups"] == [{"programs": ["PAYCALC", "TAXCALC"], "tables": ["PAYROLL.TAXRATES"]}]
    assert {"from": "J:PAYJOB", "to": "P:PAYCALC", "kind": "runs"} in r["links"]
    alt = I.analyse(INV.replace("## OLDRPT.cbl", "## OLDRPT.cbl\n").replace("PROGRAM-ID. TAXCALC.\n", "PROGRAM-ID. TAXCALC.\n") + "\n")
    assert alt["totals"]["programs"] == 4
    with pytest.raises(I.InventoryError):
        I.analyse("## X\nnothing here")
    lay = L.analyse(OUT)["rows"]
    pf = P.prove(PROOF, lay, keys="O-ID")
    kinds = {(d["field"], d["kind"]) for d in pf["diffs"]}
    assert not pf["proved"] and pf["differ"] == 3 and pf["only_old"] == 1 and pf["only_new"] == 1
    assert {("O-PAY", "rounding"), ("O-PAY", "sign"), ("O-NAME", "case"), ("(record)", "only_old"), ("(record)", "only_new")} <= kinds
    assert P.prove(SAME, lay, keys="O-ID")["proved"] is True
    assert P.prove(PROOF, lay, keys="O-ID", ignore="O-PAY,O-NAME")["differ"] == 0
    re_ = P.prove("## old\nb,1\nA,2\n1,3\n## new\n1,3\nA,2\nb,1\n", mode="lines")
    assert re_["reordered"] and "EBCDIC order" in re_["issues"][0]["text"]
    csv_ = P.prove("## old\nid,amt\n1,10.50\n2,3.33\n## new\nid,amt\n1,10.50\n2,3.34\n", keys="id", tolerance="0.01")
    assert csv_["mode"] == "csv" and csv_["proved"] and csv_["within"] == 1
    for bad in ("no headings", "## old\na\n## new\nb\n"):
        if bad == "no headings":
            with pytest.raises(P.ProofError):
                P.prove(bad)
    with pytest.raises(P.ProofError):
        P.prove(PROOF, lay, keys="NOPE")
    w = CI.workflow("java -jar app.jar tests/in.txt > output.txt", "mvn -q package", layout=lay, keys="O-ID", setup="java")
    y = yaml.safe_load(w["yaml"])
    steps = y["jobs"]["output"]["steps"]
    assert y["permissions"] == {"contents": "read"} and steps[1]["uses"] == "actions/setup-java@v4" and w["fields"] == 3
    for bad in (dict(run_cmd=""), dict(run_cmd="x ${{ secrets.A }}"), dict(run_cmd="x", golden="../x"), dict(run_cmd="x", keys="O-ID"),
                dict(run_cmd="x", layout=lay, keys="NOPE")):
        with pytest.raises(CI.CiError):
            CI.workflow(**bad)
    code = w["compare"].replace("\n          ", "\n").strip()
    (tmp_path / "g").write_text("\n".join(OLD) + "\n")
    (tmp_path / "n").write_text("\n".join(reversed(OLD)) + "\n")
    run = lambda: subprocess.run([sys.executable, "-I", "-c", code, str(tmp_path / "g"), str(tmp_path / "n")], capture_output=True, text=True,   # noqa: E731
                                 env={"PATH": os.environ.get("PATH", ""), "GITHUB_STEP_SUMMARY": str(tmp_path / "s.md")})
    assert run().returncode == 0
    (tmp_path / "n").write_text("\n".join(NEW) + "\n")
    out = run()
    assert out.returncode == 1 and "O-PAY" in out.stdout and "| A00004 |" in (tmp_path / "s.md").read_text().replace("('A00004',)", "A00004") or "A00004" in (tmp_path / "s.md").read_text()


def test_hire_chat_wiring_store_and_guards(mfc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert mfc.summary(T)["hired"] is False and "Hire me from AI Employees" in mfc.greeting(T)
    with pytest.raises(PermissionError):
        mfc.do(T, "add", {"kind": "program", "text": COBOL})
    _hire()
    d = mfc.summary(T)
    assert d["hired"] and "runs nothing on your mainframe" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"programs", "settings"}
    chat = mfc.current(T)
    assert mfc.is_mainframe(chat["id"]) and mfc.owns(T, chat["id"]) and "<mainframe_desk>" in mfc.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_mfc.is_mainframe(conversation_id)" in s_ and "adm.admit_families(_mfc.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"mainframe"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/mainframe")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "mfdesk.js" in r.text
    html = (root / "server/app/static/console/mfdesk.html").read_text()
    for x in ("chatkit.js", "mfdesk.css", "mfdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/mainframe')" in (root / "server/app/static/console/v2.js").read_text()
    assert "mainframe_arch: 'mfdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["mainframe_arch"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["mainframe_desk"] in mfc.FAMILIES and "mainframe_desk" in HANDLERS
    pg = mfc.do(T, "add", {"kind": "program", "text": COBOL})
    assert pg["number"] == "P-0001" and pg["title"] == "Program PAYCALC" and pg["brief"]["dead"] == 1 and pg["brief"]["bad"] is False
    cb = mfc.do(T, "add", {"kind": "copybook", "text": OUT})
    assert cb["number"] == "C-0001" and cb["brief"]["length"] == 23
    jb = mfc.do(T, "add", {"kind": "jcl", "text": JCL})
    assert jb["number"] == "J-0001" and jb["title"] == "JCL PAYJOB"
    iv = mfc.do(T, "add", {"kind": "inventory", "text": INV})
    assert iv["number"] == "I-0001" and iv["brief"]["waves"] == 2 and iv["brief"]["missing"] == 1
    assert mfc.summary(T)["desk"]["map"]["programs"] == 4
    pf = mfc.do(T, "add", {"kind": "proof", "text": PROOF, "inputs": {"copybook": "C-0001", "keys": "O-ID"}})
    assert pf["number"] == "D-0001" and pf["brief"]["bad"] and pf["brief"]["differ"] == 3
    assert any(n["go"] == "proof/" + pf["id"] for n in mfc.summary(T)["desk"]["needs"])
    ok = mfc.do(T, "add", {"kind": "proof", "text": SAME, "inputs": {"copybook": "C-0001", "keys": "O-ID"}})
    assert ok["brief"]["proved"] is True and mfc.summary(T)["desk"]["proofs"] == {"n": 2, "proved": 1, "latest": "D-0002", "latest_ok": True}
    with pytest.raises(mfc.MfDeskError):
        mfc.do(T, "add", {"kind": "proof", "text": PROOF, "inputs": {"copybook": "P-0001"}})
    assert mfc.do(T, "ci", {})["missing"] is True
    st = mfc.do(T, "settings", {"run_cmd": "java -jar pay.jar in.txt > output.txt", "ci_copybook": "C-0001", "keys": "O-ID", "setup": "java", "encoding": "cp1140"})
    assert st["ci_copybook"] == "C-0001" and st["encoding"] == "cp1140"
    w = mfc.do(T, "ci", {})
    assert w["fields"] == 3 and "setup-java" in w["yaml"] and yaml.safe_load(w["yaml"])
    mfc.forget(T)
    assert "cp1140" in mfc.block(T) and "copybook C-0001" in mfc.block(T)
    mk = mfc.do(T, "mark", {"id": pf["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "proof/" + pf["id"] for n in mfc.summary(T)["desk"]["needs"])
    import asyncio
    from app.agent import mainframe_tools as MT
    from app.agent.tools import Ctx
    out = asyncio.run(MT.mainframe_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="copybook", text=CPY, inputs={"sample": REC}))
    assert any(f["name"] == "CUST-BAL" and f["value"] == "123.45" for f in out["decoded"])
    out = asyncio.run(MT.mainframe_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="inventory", text=INV))
    assert out["waves"][0]["wave"] == 1 and any(p["approach"] == "Retire?" for p in out["programs"])
    out = asyncio.run(MT.mainframe_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/output-check.yml"
    with pytest.raises(PermissionError):
        mfc.do(T, "settings", {"run_cmd": "my password is hunter2"})
    assert mfc.do(T, "add", {"kind": "program", "text": COBOL.replace("STOP RUN.", "DISPLAY 'password = hunter2'\n           STOP RUN.")})["kind"] == "program"
    for bad in ({"encoding": "utf-16"}, {"target": "rust"}, {"setup": "cobol85"}, {"ci_copybook": "J-0001"}, {"golden": "../../etc/x"}):
        with pytest.raises((mfc.MfDeskError, PermissionError)):
            mfc.do(T, "settings", bad)
    with pytest.raises(mfc.MfDeskError):
        mfc.do(T, "add", {"kind": "jcl", "text": ""})
    with pytest.raises(mfc.MfDeskError):
        mfc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "mainframe_arch")
    assert mfc.do(T, "get", {"id": pg["id"]})["id"] == pg["id"] and mfc.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        mfc.do(T, "add", {"kind": "program", "text": COBOL})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def mf_server(mfc, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
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
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(mfc, mf_server):
    base, browser, key = mf_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    def put(pg, form, name, text):
        pg.eval_on_selector(f"form[data-form={form}] [name={name}]", "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); }", text)

    def submit(pg, form, text, sel):
        put(pg, form, "text", text)
        pg.click(f"form[data-form={form}] [type=submit]")
        pg.wait_for_selector(sel, timeout=60000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/mainframe")
    pg.wait_for_selector(".mfk-path", timeout=20000)
    snap(pg, "mf-today-empty-1440")
    go(pg, "#/programs", "form[data-form=program]")
    submit(pg, "program", COBOL, ".mfk-plist")
    assert "8000-OLD-REPORT" in pg.inner_text(".mfk-plist") and pg.locator(".mfk-plist div.dead").count() == 1 and "PAYROLL.TAXRATES" in pg.inner_text("#mfPage")
    snap(pg, "mf-program-1440")
    go(pg, "#/data", "form[data-form=copybook]")
    put(pg, "copybook", "sample", REC)
    submit(pg, "copybook", CPY, ".mfk-bytes")
    assert "123.45" in pg.inner_text(".mfk-fields") and "-12.34" in pg.inner_text(".mfk-fields") and "CREATE TABLE customer_rec" in pg.inner_text("#mfPage")
    snap(pg, "mf-layout-1440")
    go(pg, "#/data", "form[data-form=copybook]")
    submit(pg, "copybook", OUT, ".mfk-bytes")
    go(pg, "#/batch", "form[data-form=jcl]")
    submit(pg, "jcl", JCL, ".mfk-steps")
    assert "PAYCALC" in pg.inner_text(".mfk-steps") and "SORT FIELDS=(1,6,CH,A)" in pg.inner_text(".mfk-steps")
    snap(pg, "mf-jcl-1440")
    go(pg, "#/map", "form[data-form=inventory]")
    submit(pg, "inventory", INV, ".mfk-graph")
    assert pg.locator(".mfk-graph .nd").count() == 4 and "Retire?" in pg.inner_text("#mfPage") and "Wave 2" in pg.inner_text(".mfk-graph")
    snap(pg, "mf-map-1440")
    go(pg, "#/proof", "form[data-form=proof]")
    put(pg, "proof", "old", "\n".join(OLD))
    put(pg, "proof", "new", "\n".join(NEW))
    pg.select_option("form[data-form=proof] [name=copybook]", label=pg.eval_on_selector("form[data-form=proof] [name=copybook] option:nth-child(2)", "o => o.textContent"))
    pg.fill("form[data-form=proof] [name=keys]", "O-ID")
    pg.click("form[data-form=proof] [type=submit]")
    pg.wait_for_selector(".mfk-diff", timeout=60000)
    assert "differs" in pg.inner_text(".mfk-proved").lower() and "rounding" in pg.inner_text(".mfk-diff").lower() and "sign" in pg.inner_text(".mfk-diff").lower()
    snap(pg, "mf-proof-1440")
    go(pg, "#/ci", "text=Set the command")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=run_cmd]", "java -jar pay.jar in.txt > output.txt")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=output-check.yml")
    assert "java -jar pay.jar" in pg.inner_text("#mfPage")
    snap(pg, "mf-ci-1440")
    go(pg, "#/today", ".mfk-list")
    assert "4" in pg.inner_text(".cs-hero")
    snap(pg, "mf-today-1440")
    for route, sel in (("#/today", ".mfk-list"), ("#/programs", ".mfk-item"), ("#/data", ".mfk-item"), ("#/batch", ".mfk-item"), ("#/map", ".mfk-item"),
                       ("#/proof", ".mfk-item"), ("#/ci", "text=output-check.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#mfPage *')].filter(e => !e.closest('pre,textarea,table,svg,.mfk-graph') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/map", "#/proof", "#/data"):
        go(pg, route, ".mfk-item")
        pg.locator(".mfk-item").first.click()
        pg.wait_for_selector(".mfk-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
        snap(pg, "mf-" + route[2:] + "-390")
    assert not errs, errs
