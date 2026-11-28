"""v0.999.237 DATA STEPS + EXPRESSIONS (R3 of the Hoola Route plan; owner: "GO R3"; built as 0.999.235, their DIGITAL ASSETS DESK and COMPUTER TOP BAR took 0.999.235-0.999.236).

Expressions in {{ }} do maths and call a fixed list of functions on her data only; a plain {{a.b}} is unchanged; nothing of
Python is reachable. A new step type `data` sorts, limits, removes duplicates, summarises, splits out, compares, keeps / renames
fields, sets several fields, works with dates, text formats (HTML / XML / CSV / JSON / Base64 / URL), makes and reads files
(CSV / Excel / PDF) and hashes. A malformed expression is refused when the route is saved; the editor shows each box's result
live from the route's newest data.
"""
import asyncio
import base64
import hashlib
import hmac
import os
import shutil
import threading
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_data as DD
from app.agent import dhara_tools as D
from app.agent.tools import Ctx, ToolError

CTX = {"vars": {"a": 5, "name": "asha rao", "due": "2026-01-30", "rows": [{"id": 1, "n": 3, "city": "Pune"}, {"id": 2, "n": 4, "city": "Oslo"},
                                                                         {"id": 3, "n": 3, "city": "Pune"}]},
       "steps": {"order": {"output": {"total": 1000, "lines": [{"sku": "a", "tags": ["x", "y"]}, {"sku": "b", "tags": ["z"]}]}}},
       "item": {"n": 7}}


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def test_expressions_do_maths_and_functions():
    R = lambda e: D.resolve(e, CTX)  # noqa: E731
    assert R("{{vars.a}}") == 5 and R("{{ vars.a * 2 + 1 }}") == 11
    assert R("{{ steps.order.output.total * 1.18 }}") == pytest.approx(1180.0)
    assert R("Hi {{ title(vars.name) }}, total {{ round(steps.order.output.total / 3, 2) }}") == "Hi Asha Rao, total 333.33"
    assert R("{{ 'big' if vars.a > 3 else 'small' }}") == "big"
    assert R("{{ vars.rows[1].city }}") == "Oslo" and R("{{ vars.rows.1.city }}") == "Oslo"
    assert R("{{ sum(pluck(vars.rows, 'n')) }}") == 10 and R("{{ count(vars.rows) }}") == 3
    assert R("{{ date_add(vars.due, 1, 'months') }}") == "2026-02-28"
    assert R("{{ date_diff('2026-01-01', '2026-01-31') }}") == 30
    assert R("{{ date_format('2026-12-05', '%d %b %Y') }}") == "05 Dec 2026"
    assert R("{{ item.n + 1 }}") == 8
    assert R("{{ default(vars.nope, 'none') }}") == "none"
    assert R("{{ join(sort(pluck(vars.rows, 'city')), ' / ') }}") == "Oslo / Pune / Pune"
    assert R("{{ len(vars.name) > 3 and contains(vars.name, 'rao') }}") is True


def test_nothing_of_python_is_reachable():
    for bad in ("__import__('os')", "vars.__class__", "vars.a.__class__.__mro__", "().__class__", "open('x')",
                "(lambda: 1)()", "[x for x in vars.rows]", "vars.a ** 100", "'a' * 3", "eval('1')", "getattr(vars, 'a')",
                "f'{vars}'", "{1, 2}"):
        out = D.resolve("{{ " + bad + " }}", CTX)
        assert out is None or out == "{{ " + bad + " }}", (bad, out)
    assert DD.check("__import__('os')") and DD.check("(lambda: 1)()") and DD.check("[x for x in vars.rows]")
    assert DD.check("vars.a * 2 + round(1.5)") == ""
    # a plain path keeps its old meaning; text that fails stays as written
    assert D.resolve("{{steps.order.output.total}}", CTX) == 1000
    assert D.resolve("Code {{ 1 / 0 }} here", CTX) == "Code {{ 1 / 0 }} here"


def test_a_bad_expression_is_refused_on_save():
    with pytest.raises(ToolError) as e:
        D.validate_steps([{"id": "n", "type": "notify", "text": "Total {{ vars.a * }}"}])
    assert "not a valid expression" in str(e.value)
    with pytest.raises(ToolError) as e:
        D.validate_steps([{"id": "n", "type": "notify", "text": "{{ shell(vars.a) }}"}])
    assert "Unknown function 'shell'" in str(e.value)
    D.validate_steps([{"id": "n", "type": "notify", "text": "Total {{ round(vars.a * 1.18, 2) }} for {{vars.name}}"}])
    with pytest.raises(ToolError):
        D.validate_steps([{"id": "d", "type": "data", "op": "nope"}])
    with pytest.raises(ToolError) as e:
        D.validate_steps([{"id": "d", "type": "data", "op": "sort"}])
    assert "sort needs items" in str(e.value)
    with pytest.raises(ToolError):
        D.validate_steps([{"id": "d", "type": "data", "op": "text", "action": "shell", "value": "x"}])


def _op(**step):
    return DD.run("t-data", {"id": "d", "type": "data", **step}, CTX, D.resolve)


def test_the_data_operations():
    rows = "{{vars.rows}}"
    assert [r["id"] for r in _op(op="sort", items=rows, by="city", order="desc")] == [1, 3, 2]
    assert [r["id"] for r in _op(op="limit", items=rows, count=2, keep="last")] == [2, 3]
    assert [r["id"] for r in _op(op="dedupe", items=rows, by="city")] == [1, 2]
    assert _op(op="aggregate", items=rows, field="n", how="sum") == 10
    assert _op(op="aggregate", items=rows, field="n", how="avg") == pytest.approx(3.333333, rel=1e-4)
    assert _op(op="aggregate", items=rows, field="city", how="join", sep="|") == "Pune|Oslo|Pune"
    assert _op(op="aggregate", items=rows, how="count") == 3
    assert _op(op="split", items="{{steps.order.output.lines}}", field="tags") == ["x", "y", "z"]
    cmp = _op(op="compare", a=[{"id": 1, "v": 1}, {"id": 2, "v": 1}], b=[{"id": 2, "v": 2}, {"id": 3, "v": 1}], key="id")
    assert cmp["counts"] == {"added": 1, "removed": 1, "changed": 1, "same": 0}
    assert _op(op="keep_fields", items=rows, fields="id, city")[0] == {"id": 1, "city": "Pune"}
    assert _op(op="keep_fields", items=rows, fields="city", mode="drop")[0] == {"id": 1, "n": 3}
    assert _op(op="rename", items={"a": 1, "b": 2}, map={"a": "x"}) == {"x": 1, "b": 2}
    assert _op(op="fields", values={"total": "{{ steps.order.output.total * 2 }}", "who": "{{ upper(vars.name) }}"}) == {"total": 2000, "who": "ASHA RAO"}
    assert _op(op="date", action="add", value="2026-03-31", amount=1, unit="months") == "2026-04-30"
    assert _op(op="date", action="diff", value="2026-01-01T00:00:00", other="2026-01-01T06:00:00", unit="hours") == 6
    assert _op(op="date", action="format", value="2026-06-01T12:00:00+00:00", format="%H:%M", tz="Asia/Tokyo") == "21:00"
    html = "<html><body><h2>One</h2><a class='x' href='/a'>A</a><script>bad()</script><h2>Two</h2></body></html>"
    assert _op(op="text", action="html_select", value=html, selector="h2") == ["One", "Two"]
    assert _op(op="text", action="html_select", value=html, selector="a.x", attr="href") == ["/a"]
    assert "bad()" not in _op(op="text", action="html_text", value=html)
    assert _op(op="text", action="xml_to_data", value="<o id='7'><i>a</i><i>b</i></o>") == {"o": {"@id": "7", "i": ["a", "b"]}}
    with pytest.raises(DD.ExprError):
        _op(op="text", action="xml_to_data", value="<!DOCTYPE x [<!ENTITY e 'x'>]><o>&e;</o>")
    assert _op(op="text", action="csv_to_rows", value="a,b\n1,2\n") == [{"a": "1", "b": "2"}]
    assert _op(op="text", action="rows_to_csv", value=[{"a": 1, "b": 2}]).splitlines() == ["a,b", "1,2"]
    b64 = _op(op="text", action="base64_encode", value="héllo")
    assert _op(op="text", action="base64_decode", value=b64) == "héllo"
    assert _op(op="text", action="url_encode", value="a b&c") == "a%20b%26c"
    assert _op(op="crypto", action="sha256", value="abc") == hashlib.sha256(b"abc").hexdigest()
    assert _op(op="crypto", action="hmac_sha256", value="msg", secret="k") == hmac.new(b"k", b"msg", hashlib.sha256).hexdigest()
    assert len(_op(op="crypto", action="uuid")) == 36 and len(_op(op="crypto", action="random", length=12)) == 12
    with pytest.raises(DD.ExprError):
        _op(op="aggregate", items="{{vars.a}}", how="sum")
    assert base64  # noqa: B018


def test_files_are_made_and_read_back(bz):
    t = "t-files"
    x = DD.run(t, {"id": "f", "type": "data", "op": "file", "action": "make_xlsx", "items": "{{vars.rows}}", "name": "cities"}, CTX, D.resolve)
    assert x["name"] == "cities.xlsx" and x["file_id"] and x["url"]
    back = DD.run(t, {"id": "r", "type": "data", "op": "file", "action": "read", "file_id": x["file_id"]}, CTX, D.resolve)
    assert back["rows"][1] == {"id": 2, "n": 4, "city": "Oslo"}
    c = DD.run(t, {"id": "f", "type": "data", "op": "file", "action": "make_csv", "items": "{{vars.rows}}", "name": "c"}, CTX, D.resolve)
    assert DD.run(t, {"id": "r", "type": "data", "op": "file", "action": "read", "file_id": c["file_id"]}, CTX, D.resolve)["rows"][0]["city"] == "Pune"
    p = DD.run(t, {"id": "f", "type": "data", "op": "file", "action": "make_pdf", "title": "Report", "value": "Total {{ steps.order.output.total }}"}, CTX, D.resolve)
    txt = DD.run(t, {"id": "r", "type": "data", "op": "file", "action": "read", "file_id": p["file_id"]}, CTX, D.resolve)["text"]
    assert "Report" in txt and "Total 1000" in txt
    with pytest.raises(DD.ExprError):
        DD.run("someone-else", {"id": "r", "type": "data", "op": "file", "action": "read", "file_id": c["file_id"]}, CTX, D.resolve)


def test_a_route_with_data_steps_runs_and_the_editor_previews(bz):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    c, t = TestClient(app), get_settings().tenant_id
    _wipe(t)
    try:
        steps = [{"id": "rows", "type": "set", "name": "rows", "value": [{"n": 3, "c": "Pune"}, {"n": 4, "c": "Oslo"}]},
                 {"id": "top", "type": "data", "op": "sort", "items": "{{vars.rows}}", "by": "n", "order": "desc"},
                 {"id": "total", "type": "data", "op": "aggregate", "items": "{{steps.top.output}}", "field": "n", "how": "sum"},
                 {"id": "say", "type": "notify", "text": "Top {{ steps.top.output[0].c }}, total {{ steps.total.output * 10 }}"}]
        _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name="data_flow", steps=steps))
        wf = D.get_workflow(t, name="data_flow")
        rid = D.create_run(t, wf)
        _run(D.execute_run(t, rid))
        r = D.get_run(t, rid)
        assert r["status"] == "done", r
        assert r["context"]["steps"]["top"]["output"][0]["c"] == "Oslo" and r["context"]["steps"]["total"]["output"] == 7
        pv = c.post(f"/api/route/routes/{wf['id']}/eval", json={"text": "Top {{ steps.top.output[0].c }} = {{ steps.total.output * 10 }}"}).json()
        assert pv["value"] == "Top Oslo = 70" and pv["errors"] == [] and pv["has_data"]
        bad = c.post(f"/api/route/routes/{wf['id']}/eval", json={"text": "{{ steps.total.output / 0 }}"}).json()
        assert bad["errors"] and "Division by zero" in bad["errors"][0]["error"]
        kinds = {k["key"] for k in c.get("/api/route/catalog").json()["kinds"]}
        assert {"sort", "aggregate", "date", "text", "file", "crypto", "fields", "compare"} <= kinds
        # a step test of a data step works and can be pinned
        st = c.post(f"/api/route/routes/{wf['id']}/steps/total/test", json={}).json()
        assert st["ok"] and st["output"] == 7
    finally:
        _wipe(t)


def test_page_knows_the_data_steps():
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.js").read_text()
    for part in ("DATAF", "SHOWIF", "previewSoon", "/eval`", "Summarise", "Make or read a file", "data-prev"):
        assert part in js, part
    css = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.css").read_text()
    assert ".fprev{" in css


# ---------------------------------------------------------------- a real browser
@pytest.fixture
def br3(bz, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name="sum_flow",
                      steps=[{"id": "rows", "type": "set", "name": "rows", "value": [{"n": 3}, {"n": 4}]}]))
    wf = D.get_workflow(t, name="sum_flow")
    _run(D.execute_run(t, D.create_run(t, wf)))
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
    try:
        pw = sync_api.sync_playwright().start()
        try:
            b = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        yield f"http://127.0.0.1:{port}/console/route", b, KEY, t
        b.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)
        _wipe(t)


def test_add_a_data_step_in_a_real_browser(br3):
    base, b, key, t = br3
    wf = D.get_workflow(t, name="sum_flow")
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(base + "#/r/" + wf["id"])
    p.wait_for_selector(".nd[data-node='rows']")
    p.click(".nd[data-node='rows'] .addaf", force=True)
    p.fill("#addQ", "summarise")
    p.wait_for_selector("#addList .arow[data-kind='aggregate']")
    p.click("#addList .arow[data-kind='aggregate']")
    p.wait_for_selector("#edPanel [data-k='d:items']")
    p.fill("#edPanel [data-k='d:items']", "{{vars.rows}}")
    p.fill("#edPanel [data-k='d:field']", "n")
    pid = p.get_attribute("#edPanel [data-k='d:items']", "id")
    p.wait_for_function(f"() => {{ const e = document.querySelector('[data-prev=\"{pid}\"]'); return e && !e.hidden && e.innerText.includes('\"n\":3'); }}", timeout=10000)
    p.select_option("#edPanel [data-k='d:how']", "join")
    p.wait_for_selector("#edPanel [data-k='d:sep']")
    p.select_option("#edPanel [data-k='d:how']", "sum")
    p.click("#edSave")
    p.wait_for_function("() => document.querySelector('#edState').innerText === 'Saved'", timeout=10000)
    got = D.get_workflow(t, wf_id=wf["id"])["steps"][1]
    assert got["type"] == "data" and got["op"] == "aggregate" and got["items"] == "{{vars.rows}}" and got["how"] == "sum"
    assert "Summarise" in p.inner_text("#world")
    assert not errs, errs
