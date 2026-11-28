"""v0.999.258 MAKE PARITY (built as 0.999.254) - Hoola Route checked against Make feature by feature (owner: "GET EXTREEM DEEP FIND ALL
HOOLA ROUTE TOOL IS FUCTIONATING PERFECTLY SAME AS MAKE OR NOT --- WE WANT ALL MAKE FUCTION IN IT. WITH END TO END
FUCTIONING"). Each Make piece Route did not have is pinned here, end to end through the real engine:

  - Make's functions (general, math, text, date with Make's tokens, array) and keywords inside {{ }}; {{run.*}}
  - data stores: structure, add / update / get / exists / delete / delete_all / search / count / increment, CSV, and a
    Rollback that really takes the run's writes back
  - Tools: set several values, get, the increment function (across runs and per run), save a route variable
  - the Repeater, and loops that collect (Make's array / text / numeric aggregators)
  - error handler routes (steps that run before the directive, with {{error.message}})
  - the web request at Make's HTTP v4 level: every method, JSON / form / multipart / raw bodies, query, timeout,
    parse off, errors on / off, pagination, download a file, resolve a URL, shared cookies
  - Text parser (match pattern, replace), Make XML, table text, Markdown, ZIP in and out
  - scenario settings: process in order, confidential, keep incomplete, auto commit; the webhook queue (calls are
    never refused for coming fast), calls kept while off, IP restriction, the caller's headers
  - schedule start date; "choose where to start" for app events; operations counted
  - a Make blueprint brought in; the Grid
"""
import asyncio
import io
import json
import shutil
import threading
import time
import zipfile
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_data as DD
from app.agent import dhara_tools as D
from app.agent.tools import Ctx, HANDLERS, ToolError
from app.route import store as DS


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def _save(t, name, steps, **kw):
    return _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name=name, steps=steps, **kw))


def _go(t, name, vars_=None):
    rid = D.create_run(t, D.get_workflow(t, name=name), vars_=vars_ or {})
    _run(D.execute_run(t, rid))
    return D.get_run(t, rid)


def _out(r, sid):
    return r["context"]["steps"][sid]["output"]


@pytest.fixture
def T(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    D._RUNNING.clear()
    t = "r254_make"
    _wipe(t)
    yield t
    D._RUNNING.clear()
    _wipe(t)


# ---------------------------------------------------------------- Make's functions
@pytest.mark.parametrize("expr,want", [
    ('if(vars.a > 3, "big", "small")', "big"),
    ('ifempty(vars.none, "x")', "x"),
    ('switch(vars.a, 1, "one", 5, "five", "else")', "five"),
    ('omit({"a": 1, "b": 2}, "a")', {"b": 2}),
    ('pick({"a": 1, "b": 2}, "a")', {"a": 1}),
    ('formatDate("2026-12-05T14:30:00", "Do MMMM YYYY, h:mm A")', "5th December 2026, 2:30 PM"),
    ('formatDate("2026-12-05", "dddd DD/MM/YY")', "Saturday 05/12/26"),
    ('parseDate("05/12/2026", "DD/MM/YYYY")', "2026-12-05"),
    ('addMonths("2026-01-31", 1)', "2026-02-28"),
    ('setDay("2026-12-05", "monday")', "2026-11-30"),
    ('formatNumber(1234567.891, 2, ",", ".")', "1.234.567,89"),
    ('parseNumber("1.234,5", ",")', 1234.5),
    ('trunc(3.789, 1)', 3.7),
    ('median(1, 5, 3, 10)', 4.0),
    ('startcase("priya sharma")', "Priya Sharma"),
    ('substring("Hoola Route", 0, 5)', "Hoola"),
    ('indexOf("abcabc", "c")', 2),
    ('replace("a1b22", "/\\d+/g", "#")', "a#b#"),
    ('stripHTML("<b>hi</b> there")', "hi there"),
    ('map([{"a": 1, "t": "x"}, {"a": 2, "t": "y"}], "a")', [1, 2]),
    ('flatten([1, [2, [3]]])', [1, 2, 3]),
    ('merge([1], [2, 3])', [1, 2, 3]),
    ('distinct([{"k": 1}, {"k": 1}, {"k": 2}], "k")', [{"k": 1}, {"k": 2}]),
    ('toCollection([{"k": "a", "v": 1}], "k", "v")', {"a": 1}),
    ('arrayDiff([1, 2, 3], [2])', [1, 3]),
    ('sort([{"n": "b"}, {"n": "A"}], "asc ci", "n")', [{"n": "A"}, {"n": "b"}]),
    ('sha256("abc")[:8]', "ba7816bf"),
    ('newline', "\n"),
    ('length(emptyarray)', 0),
])
def test_make_functions(expr, want):
    assert DD.evaluate(expr, {"vars": {"a": 5}}) == want
    assert DD.check(expr) == ""


def test_keywords_and_run_variables(T):
    _save(T, "kw", [{"id": "a", "type": "set", "name": "x", "value": "{{run.route}}|{{uuid}}|{{now}}"}])
    r = _go(T, "kw")
    route, uid, now = r["context"]["vars"]["x"].split("|")
    assert route == "kw" and len(uid) == 36 and now[:4].isdigit()
    assert r["context"]["run"]["id"] == r["id"]


# ---------------------------------------------------------------- data stores
def test_data_store_every_operation_and_its_structure(T):
    DS.save_store(T, "customers", [{"name": "email", "type": "text", "required": True}, {"name": "visits", "type": "number"},
                                   {"name": "vip", "type": "boolean"}])
    _save(T, "crm", [
        {"id": "add", "type": "store", "op": "add", "store": "customers", "key": "{{vars.email}}",
         "data": {"email": "{{vars.email}}", "visits": "1", "vip": "yes"}},
        {"id": "two", "type": "store", "op": "add", "store": "customers", "key": "b@x.com", "data": {"email": "b@x.com", "visits": 9}},
        {"id": "upd", "type": "store", "op": "update", "store": "customers", "key": "{{vars.email}}", "data": {"visits": 4}},
        {"id": "inc", "type": "store", "op": "increment", "store": "customers", "key": "{{vars.email}}", "field": "visits", "by": 2},
        {"id": "get", "type": "store", "op": "get", "store": "customers", "key": "{{vars.email}}"},
        {"id": "has", "type": "store", "op": "exists", "store": "customers", "key": "nobody@x.com"},
        {"id": "find", "type": "store", "op": "search", "store": "customers", "filter": {"field": "visits", "op": "gt", "value": 5},
         "sort": "visits", "order": "desc"},
        {"id": "n", "type": "store", "op": "count", "store": "customers"},
        {"id": "del", "type": "store", "op": "delete", "store": "customers", "key": "b@x.com"},
    ])
    r = _go(T, "crm", {"email": "a@x.com"})
    assert r["status"] == "done", r.get("error")
    assert _out(r, "get") == {"exists": True, "key": "a@x.com", "data": {"email": "a@x.com", "visits": 6, "vip": True}}
    assert _out(r, "has")["exists"] is False
    assert [x["key"] for x in _out(r, "find")] == ["b@x.com", "a@x.com"]
    assert _out(r, "n") == {"count": 2}
    assert DS.get_store(T, "customers")["records"] == 1
    _save(T, "bad", [{"id": "add", "type": "store", "op": "add", "store": "customers", "key": "z", "data": {"visits": 1}}])
    assert "Required and empty: email" in (_go(T, "bad")["error"] or "")
    with pytest.raises(ToolError):
        _save(T, "wipe", [{"id": "w", "type": "store", "op": "delete_all", "store": "customers"}])   # needs confirm


def test_rollback_takes_the_runs_data_store_writes_back(T):
    DS.save_store(T, "stock", [])
    DS.put(T, "stock", "tea", {"n": 10})
    _save(T, "sell", [
        {"id": "take", "type": "store", "op": "increment", "store": "stock", "key": "tea", "field": "n", "by": -3},
        {"id": "new", "type": "store", "op": "add", "store": "stock", "key": "order_1", "data": {"item": "tea"}},
        {"id": "pay", "type": "code", "code": "raise ValueError('the card was declined')", "on_error": {"do": "rollback"}}])
    r = _go(T, "sell")
    assert r["status"] == "failed" and "2 data store changes taken back" in r["error"]
    rows, total = DS.records(T, "stock")
    assert total == 1 and rows[0]["data"] == {"n": 10}, "Make's Rollback undoes the data store writes of the run"
    _save(T, "sell2", [
        {"id": "take", "type": "store", "op": "increment", "store": "stock", "key": "tea", "field": "n", "by": -3},
        {"id": "pay", "type": "code", "code": "raise ValueError('x')", "on_error": {"do": "commit"}}])
    assert _go(T, "sell2")["status"] == "done"
    assert DS.records(T, "stock")[0][0]["data"]["n"] == 7, "commit keeps them"


def test_data_store_csv_round_trip_and_the_size_limit(T):
    DS.save_store(T, "tiny", [{"name": "name", "type": "text"}, {"name": "tags", "type": "array"}], max_kb=16)
    DS.import_csv(T, "tiny", 'key,name,tags\nk1,Asha,"[""a""]"\nk2,Ben,\n')
    text = DS.export_csv(T, "tiny")
    assert text.splitlines()[0] == "key,name,tags" and "k1,Asha" in text
    with pytest.raises(DS.StoreError):
        DS.import_csv(T, "tiny", "key,name\nk3,x\n" + "".join(f"k{i},{'y' * 900}\n" for i in range(40)))
    assert DS.records(T, "tiny")[1] == 2, "a CSV that does not fit is brought in whole or not at all"


# ---------------------------------------------------------------- tools: variables, counter, repeater, aggregators
def test_variables_counter_and_saved_variable(T):
    _save(T, "tools", [
        {"id": "many", "type": "var", "op": "set_many", "values": {"a": 1, "b": "{{vars.a + 1}}"}},
        {"id": "both", "type": "var", "op": "get_many", "names": "a, b"},
        {"id": "c", "type": "var", "op": "increment", "name": "orders"},
        {"id": "c_run", "type": "var", "op": "increment", "name": "rounds", "reset": "run"},
        {"id": "keep", "type": "var", "op": "save", "name": "last_total", "value": "{{vars.b * 10}}"}])
    r1, r2 = _go(T, "tools"), _go(T, "tools")
    assert _out(r1, "both") == {"a": 1, "b": 2}
    assert _out(r1, "c")["value"] == 1 and _out(r2, "c")["value"] == 2, "the increment function counts across runs"
    assert _out(r2, "c_run")["value"] == 1, "...or starts again every run"
    from app.route import workspace as WS
    assert WS.env(T)["LAST_TOTAL"] == 20


def test_repeater_and_aggregators(T):
    _save(T, "agg", [
        {"id": "rep", "type": "loop", "repeat": {"times": 4, "start": 10, "step": 5}, "collect": "{{item}}", "join": "-",
         "body": [{"id": "x", "type": "set", "name": "n", "value": "{{item}}"}]},
        {"id": "sum", "type": "data", "op": "aggregate", "items": "{{steps.rep.output.results}}", "how": "sum"},
        {"id": "each", "type": "loop", "items": "{{vars.lines}}", "collect": "{{item.qty * 2}}",
         "body": [{"id": "skip_zero", "type": "filter", "filter": {"left": "{{item.qty}}", "op": "gt", "right": 0}}]}])
    r = _go(T, "agg", {"lines": [{"qty": 1}, {"qty": 0}, {"qty": 3}]})
    assert r["status"] == "done", r.get("error")
    assert _out(r, "rep") == {"iterations": 4, "results": [10, 15, 20, 25], "text": "10-15-20-25"}
    assert _out(r, "sum") == 70
    assert _out(r, "each")["results"] == [2, 6], "a filtered round adds nothing (Make's aggregator)"


def test_error_handler_route_runs_before_the_directive(T):
    seen = []

    async def note(ctx, **kw):
        seen.append(kw.get("text"))
        return {"ok": True}
    HANDLERS["r254_note"] = note
    try:
        _save(T, "handled", [
            {"id": "call", "type": "code", "code": "raise ValueError('the shop is closed')",
             "on_error": {"do": "resume", "value": {"fallback": True},
                          "steps": [{"id": "tell", "type": "tool", "name": "r254_note", "args": {"text": "{{error.message}}"}}]}},
            {"id": "after", "type": "set", "name": "used", "value": "{{steps.call.output.fallback}}"},
            {"id": "inner", "type": "loop", "items": [1], "body": [
                {"id": "deep", "type": "code", "code": "raise ValueError('deep')",
                 "on_error": {"steps": [{"id": "tell2", "type": "tool", "name": "r254_note", "args": {"text": "inner {{error.step}}"}}]}}]}])
        r = _go(T, "handled")
        assert r["status"] == "done", r.get("error")
        assert "the shop is closed" in seen[0] and seen[1] == "inner deep"
        assert r["context"]["vars"]["used"] is True
        assert "error" not in r["context"], "the error is only there for its handler"
    finally:
        HANDLERS.pop("r254_note", None)
    with pytest.raises(ToolError):
        _save(T, "bad_h", [{"id": "c", "type": "code", "code": "x",
                            "on_error": {"do": "ignore", "steps": [{"id": "w", "type": "approval", "question": "?"}]}}])


# ---------------------------------------------------------------- the web request (Make's HTTP v4)
def test_web_request_methods_bodies_pages_files(T, monkeypatch):
    import httpx
    from app.agent import scrape_tools as st
    calls = []

    def fake(method, url, params=None, headers=None, timeout=None, follow_redirects=None, cookies=None, **kw):
        calls.append({"m": method, "u": url, "p": dict(params or {}), "h": dict(headers or {}), "t": timeout, "kw": kw, "ck": cookies})
        req = httpx.Request(method, url)
        if "pages" in url:
            off = int((params or {}).get("offset", 0))
            items = [{"i": n} for n in range(off, min(off + 2, 5))]
            return httpx.Response(200, json={"data": {"items": items}}, request=req)
        if "file" in url:
            return httpx.Response(200, content=b"%PDF-1.4 hi", headers={"content-disposition": 'attachment; filename="bill.pdf"'}, request=req)
        if "go" in url:
            return httpx.Response(302, headers={"location": "https://api.example.com/final"}, request=req)
        if "missing" in url:
            return httpx.Response(404, json={"no": 1}, request=req)
        if "login" in url:
            return httpx.Response(200, json={"ok": 1}, headers={"set-cookie": "sid=abc; Path=/"}, request=req)
        return httpx.Response(201, json={"got": True}, request=req)
    monkeypatch.setattr(httpx, "request", fake)
    monkeypatch.setattr(st, "_guard_url", lambda u: u)
    _save(T, "web", [
        {"id": "put", "type": "http", "method": "PUT", "url": "https://api.example.com/o/1", "body_type": "json",
         "body": {"a": "{{vars.a}}"}, "query": {"v": 2}, "timeout": 7},
        {"id": "form", "type": "http", "method": "POST", "url": "https://api.example.com/f", "body_type": "form", "form": {"x": "1"}},
        {"id": "raw", "type": "http", "method": "PATCH", "url": "https://api.example.com/r", "body_type": "raw",
         "body": "<a>1</a>", "content_type": "application/xml"},
        {"id": "del", "type": "http", "method": "DELETE", "url": "https://api.example.com/o/1"},
        {"id": "pages", "type": "http", "url": "https://api.example.com/pages",
         "pagination": {"type": "offset", "items": "data.items", "param": "offset", "limit": 100}},
        {"id": "file", "type": "http", "action": "download", "url": "https://api.example.com/file"},
        {"id": "where", "type": "http", "action": "resolve", "url": "https://api.example.com/go"},
        {"id": "miss", "type": "http", "url": "https://api.example.com/missing", "fail_on_error": False},
        {"id": "login", "type": "http", "url": "https://api.example.com/login", "share_cookies": True},
        {"id": "again", "type": "http", "url": "https://api.example.com/me", "share_cookies": True}])
    r = _go(T, "web", {"a": "z"})
    assert r["status"] == "done", r.get("error")
    put = calls[0]
    assert put["m"] == "PUT" and put["kw"]["json"] == {"a": "z"} and put["p"] == {"v": 2} and put["t"] == 7.0
    assert calls[1]["kw"]["data"] == {"x": "1"} and calls[2]["h"]["Content-Type"] == "application/xml"
    assert calls[3]["m"] == "DELETE"
    assert _out(r, "pages")["count"] == 5 and _out(r, "pages")["pages"] == 4      # the empty 4th page ends it
    assert _out(r, "file")["name"] == "bill.pdf" and _out(r, "file")["size"] == 11
    assert _out(r, "where")["url"] == "https://api.example.com/final"
    assert _out(r, "miss")["status"] == 404, "with errors off, a 404 is read, not a failure"
    assert calls[-1]["ck"] == {"sid": "abc"}, "cookies shared with the run's other web requests"
    _save(T, "web404", [{"id": "miss", "type": "http", "url": "https://api.example.com/missing"}])
    assert "404" in (_go(T, "web404")["error"] or "")


# ---------------------------------------------------------------- text parser, XML, tables, markdown, zip
def test_text_parser_xml_table_markdown_zip(T):
    R = lambda v: v   # noqa: E731
    m = DD._text({"action": "regex_match", "value": "Order A-12 and B-345", "pattern": r"([A-Z])-(\d+)"}, R)
    assert m[1]["$1"] == "B" and m[1]["$2"] == "345"
    assert DD._text({"action": "regex_replace", "value": "a1b22", "pattern": r"(\d+)", "replace": "[$1]"}, R) == "a[1]b[22]"
    assert DD._text({"action": "regex_match", "value": "x", "pattern": "y", "continue_if_none": True}, R) == []
    xml = DD._text({"action": "data_to_xml", "value": {"o": {"@id": "7", "it": [{"n": "tea"}, {"n": "a & b"}]}}}, R)
    assert '<o id="7"><it><n>tea</n></it><it><n>a &amp; b</n></it></o>' in xml
    assert DD._text({"action": "xml_to_data", "value": xml}, R)["root"]["o"]["@id"] == "7"
    assert DD._text({"action": "rows_to_table", "value": [{"a": 1, "b": 2}], "column_sep": " | "}, R) == "a | b\n1 | 2"
    assert "<strong>bold</strong>" in DD._text({"action": "markdown_to_html", "value": "Some **bold**"}, R)
    f1 = DD._store(T, "a.txt", b"one")
    f2 = DD._store(T, "a.txt", b"two")
    z = DD._file(T, {"action": "zip", "items": [f1["file_id"], f2["file_id"]], "name": "both"}, R)
    from app.mailbox import service as ms
    names = zipfile.ZipFile(io.BytesIO(open(ms._file_row(T, z["file_id"]).stored_path, "rb").read())).namelist()
    assert names == ["a.txt", "a (2).txt"]
    back = DD._file(T, {"action": "unzip", "file_id": z["file_id"]}, R)
    assert [x["name"] for x in back] == ["a.txt", "a (2).txt"]


# ---------------------------------------------------------------- scenario settings, the webhook, starts
def test_in_order_confidential_and_keep_incomplete(T):
    _save(T, "ordered", [{"id": "a", "type": "set", "name": "x", "value": "{{vars.n}}"}], settings={"in_order": True, "confidential": True})
    wf = D.get_workflow(T, name="ordered")
    r1 = D.create_run(T, wf, vars_={"n": 1})
    time.sleep(0.01)
    r2 = D.create_run(T, wf, vars_={"n": 2})
    assert D._claim(T, r2, 3) is False, "process in order: the newer run waits for the older one"
    assert D._claim(T, r1, 3) is True
    _run(D.execute_run(T, r1))
    assert D._claim(T, r2, 3) is True
    _run(D.execute_run(T, r2))
    done = D.get_run(T, r2)
    assert done["status"] == "done" and all(e.get("hidden") and "output" not in e for e in done["steps_log"]), \
        "keep data confidential: the log keeps the steps, not their data"
    _save(T, "noinc", [{"id": "x", "type": "code", "code": "raise ValueError('down')", "on_error": {"do": "break", "retries": 0}}],
          settings={"keep_incomplete": False})
    r = _go(T, "noinc")
    assert r["status"] == "failed" and "not kept" in r["error"]


def test_webhook_queue_off_queue_ips_and_headers(T):
    _save(T, "hook", [{"id": "a", "type": "set", "name": "x", "value": 1}], trigger="webhook",
          settings={"queue_when_off": True, "allow_ips": ["203.0.113.0/24"]})
    import hashlib
    tok = "hook254"
    con = D._con(T)
    con.execute("UPDATE workflows SET token_hash = ? WHERE name = 'hook'", (hashlib.sha256(tok.encode()).hexdigest(),))
    con.commit()
    con.close()
    meta = {"ip": "203.0.113.9", "headers": {"X-Shop": "7", "Authorization": "secret"}, "method": "POST", "query": {"a": "1"}}
    assert D.webhook_enqueue(tok, {}, {**meta, "ip": "198.51.100.1"})["status"] == 403
    one = D.webhook_enqueue(tok, {"n": 1}, meta)
    two = D.webhook_enqueue(tok, {"n": 2}, meta)
    assert one["status"] == 202 and two["status"] == 202, "a call that comes fast waits in the queue - none is refused"
    assert "queue" in two["note"]
    q = D.get_run(T, two["run_id"])
    assert q["status"] == "sleeping" and q["pause_reason"] == "queue"
    req = D.get_run(T, one["run_id"])["context"]["vars"]["request"]
    assert req["headers"] == {"x-shop": "7"} and req["query"] == {"a": "1"}, "the caller's headers ride along (never its keys)"
    wf = D.get_workflow(T, name="hook")
    D.set_enabled(T, wf["id"], False)
    kept = D.webhook_enqueue(tok, {"n": 3}, meta)
    assert kept["status"] == 202 and D.get_run(T, kept["run_id"])["pause_reason"] == "queue_off"
    D.set_enabled(T, wf["id"], True)
    assert D.get_run(T, kept["run_id"])["pause_reason"] == "queue", "switched on: the kept calls run, oldest first"


def test_schedule_start_date_and_event_start_choice(T, monkeypatch):
    from app.route import triggers as TR
    _save(T, "later", [{"id": "a", "type": "set", "name": "x", "value": 1}], trigger="schedule",
          trigger_spec={"at": ["09:00"], "timezone": "UTC", "start_date": "2030-01-01"})
    nd = D.next_due(D.get_workflow(T, name="later"))
    assert time.strftime("%Y-%m-%d %H:%M", time.gmtime(nd)) == "2030-01-01 09:00"
    feed = {"items": [{"id": 1, "date": "2026-10-01"}, {"id": 2, "date": "2026-11-20"}]}

    async def lister(ctx, **kw):
        return dict(feed)
    monkeypatch.setitem(HANDLERS, "r254_list", lister)
    _save(T, "since", [{"id": "a", "type": "set", "name": "x", "value": "{{vars.event.id}}"}], trigger="event",
          trigger_spec={"app": "app", "tool": "r254_list", "items": "items", "every_minutes": 15, "start": "since", "since": "2026-11-01"})
    out = _run(TR.poll(T, D.get_workflow(T, name="since")))
    assert out.get("started") == 1, out
    _save(T, "all", [{"id": "a", "type": "set", "name": "x", "value": 1}], trigger="event",
          trigger_spec={"app": "app", "tool": "r254_list", "items": "items", "every_minutes": 15, "start": "all"})
    assert _run(TR.poll(T, D.get_workflow(T, name="all"))).get("started") == 2


def test_operations_are_counted(T):
    _save(T, "ops", [{"id": "each", "type": "loop", "items": [1, 2], "body": [{"id": "x", "type": "set", "name": "n", "value": 1}]},
                     {"id": "y", "type": "set", "name": "m", "value": 2}])
    r = _go(T, "ops")
    assert r["summary"]["operations"] == 4


# ---------------------------------------------------------------- Make blueprints and the Grid
_BP = {"name": "Order intake", "flow": [
    {"id": 1, "module": "gateway:CustomWebHook", "parameters": {"hook": 88}},
    {"id": 2, "module": "util:SetVariable2", "mapper": {"name": "customer", "value": "{{upper(1.name)}}"}},
    {"id": 3, "module": "builtin:BasicFeeder", "mapper": {"array": "{{1.items}}"}},
    {"id": 4, "module": "util:ComposeTransformer", "mapper": {"value": "{{3.sku}} x {{3.qty}}"},
     "filter": {"name": "real", "conditions": [[{"a": "{{3.qty}}", "o": "number:greater", "b": "0"}]]}},
    {"id": 5, "module": "util:TextAggregator", "parameters": {"feeder": 3, "rowSeparator": "\n"}, "mapper": {"value": "{{4.value}}"}},
    {"id": 6, "module": "builtin:BasicRouter", "routes": [
        {"flow": [{"id": 7, "module": "datastore:AddRecord", "parameters": {"datastore": 551},
                   "filter": {"name": "big", "conditions": [[{"a": "{{1.total}}", "o": "number:greater", "b": "1000"}]]},
                   "mapper": {"key": "{{1.id}}", "data": {"lines": "{{5.text}}", "when": "{{formatDate(now; \"YYYY-MM-DD\")}}"}},
                   "onerror": [{"id": 8, "module": "builtin:Ignore"}]}]},
        {"flow": [{"id": 9, "module": "util:FunctionIncrement", "parameters": {"reset": "never"}},
                  {"id": 10, "module": "gateway:WebhookRespond", "mapper": {"status": "200", "body": "count {{9.i}}"}}]}]},
    {"id": 11, "module": "google-sheets:addRow", "mapper": {}}],
    "metadata": {"scenario": {"sequential": True, "maxErrors": 5}}}


def test_make_blueprint_comes_in_and_runs(T):
    from app.route import makeimport as MI
    plan = MI.convert(json.dumps(_BP))
    assert plan["trigger"] == "webhook" and plan["settings"]["in_order"] is True and plan["stores"] == ["store_551"]
    assert plan["counts"]["placeholders"] == 1 and "google-sheets" in plan["report"]["placeholders"][0]["type"]
    each = [s for s in plan["steps"] if s["type"] == "loop"][0]
    assert each["items"] == "{{vars.body.items}}" and each["collect"] == "{{vars.text_4}}" and each["join"] == "\n"
    flat = json.dumps(plan["steps"])
    assert '{{formatDate(now, \\"YYYY-MM-DD\\")}}' in flat and "{{steps.each_3.output.text}}" in flat
    assert "steps.increment_9.output.value" in flat
    o = MI.bring_in(T, _BP)
    wf = D.get_workflow(T, wf_id=o["workflow_id"])
    assert not wf["enabled"] and wf["trigger_kind"] == "webhook"
    DS.save_store(T, "store_551", [])
    steps = [s for s in wf["steps"] if s["type"] != "stop"]          # the run without the 'redo' placeholder
    _save(T, "intake_try", steps)
    r = _go(T, "intake_try", {"body": {"id": "o1", "name": "asha", "total": 2000, "items": [{"sku": "tea", "qty": 2}, {"sku": "x", "qty": 0}]}})
    assert r["status"] == "done", r.get("error")
    assert DS.records(T, "store_551")[0][0]["data"]["lines"] == "tea x 2"
    with pytest.raises(MI.MakeError):
        MI.bring_in(T, _BP)                                         # its name is taken now
    with pytest.raises(MI.MakeError):
        MI.convert('{"nodes": []}')


def test_grid_draws_routes_and_what_they_touch(T):
    DS.save_store(T, "leads", [])
    _save(T, "child", [{"id": "a", "type": "set", "name": "x", "value": 1}])
    _save(T, "oops", [{"id": "a", "type": "set", "name": "x", "value": 1}])
    _save(T, "parent", [{"id": "run", "type": "subroute", "route": "child"},
                        {"id": "w", "type": "store", "op": "add", "store": "leads", "data": {}},
                        {"id": "h", "type": "http", "url": "https://api.shop.example/x"}], settings={"error_route": "oops"})
    from app.route import grid as G
    g = G.build(T)
    kinds = {(l["from"], l["to"], l["kind"]) for l in g["links"]}
    assert ("route:parent", "route:child", "runs") in kinds and ("route:parent", "route:oops", "on_error") in kinds
    assert ("route:parent", "store:leads", "writes") in kinds and ("route:parent", "web:api.shop.example", "calls") in kinds


def test_catalog_offers_the_new_steps():
    from app.route import editor as E
    keys = {k["key"] for k in E.KINDS}
    for k in ("store_add", "store_search", "store_increment", "var_set_many", "var_increment", "repeat", "aggregate_loop",
              "regex_match", "regex_replace", "make_xml", "zip", "unzip", "http_download", "http_resolve"):
        assert k in keys


# ---------------------------------------------------------------- the pages in a real browser
@pytest.fixture
def br(bz, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    import os
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    monkeypatch.setattr(D, "polite_s", 0)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    DS.save_store(t, "customers", [{"name": "email", "type": "text"}])
    DS.put(t, "customers", "a@x.com", {"email": "a@x.com"})
    _save(t, "child", [{"id": "a", "type": "set", "name": "x", "value": 1}])
    _save(t, "crm", [{"id": "w", "type": "store", "op": "add", "store": "customers", "key": "k", "data": {"email": "k"}},
                     {"id": "call", "type": "http", "method": "PUT", "url": "https://api.example.com/x", "body_type": "json", "body": {},
                      "on_error": {"do": "ignore", "steps": [{"id": "note", "type": "notify", "text": "{{error.message}}"}]}},
                     {"id": "sub", "type": "subroute", "route": "child"}])
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


def test_the_new_pages_in_a_real_browser(br):
    base, b, key, t = br
    wf = D.get_workflow(t, name="crm")
    for vw in (1440, 390):
        c = b.new_context(viewport={"width": vw, "height": 900})
        c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        p = c.new_page()
        errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.goto(base + "#/stores")
        p.wait_for_selector("text=customers")
        p.goto(base + "#/stores/customers")
        p.wait_for_selector("#dsBody tr")
        assert "a@x.com" in p.inner_text("#dsBody")
        p.goto(base + "#/grid")
        p.wait_for_selector(".gn.k-route")
        assert p.locator(".gn.k-store").count() == 1 and p.locator("svg.gedges path").count() >= 3
        p.goto(base + "#/import/make")
        p.wait_for_selector("#n8nText")
        p.fill("#n8nText", json.dumps(_BP))
        p.click("#n8nForm button[type=submit]")
        p.wait_for_selector("#n8nSave")
        assert "To redo in Hoola" in p.inner_text("#n8nOut")
        p.goto(base + f"#/r/{wf['id']}")
        p.wait_for_selector('.nd[data-node="note"]')
        p.click('.nd[data-node="call"]')
        p.wait_for_selector('[data-k="d:method"]')
        assert p.locator('[data-k="d:method"] option').count() == 7, "every method of Make's HTTP"
        assert p.locator('[data-oesteps]').is_checked()
        p.click('.nd[data-node="w"]')
        p.wait_for_selector('[data-k="d:store"]')
        assert "customers" in p.inner_text('[data-k="d:store"]')
        if vw == 390:
            p.goto(base + "#/stores/customers")
            p.wait_for_selector("#dsBody tr")
            assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        assert not errs, errs
        c.close()


def test_version():
    from app.main import APP_VERSION
    assert tuple(int(x) for x in APP_VERSION.split(".")) >= (0, 999, 258)
