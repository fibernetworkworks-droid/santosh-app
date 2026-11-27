"""v0.999.243 AI STEPS (R6 of the Hoola Route plan; owner: "GO R6").

A route step of type `ai`: write, summarise, classify (only her categories), extract (only her fields), sentiment, answer
from her files only, an agent that may use only the tools she listed (with a memory per route / per key), and a Switch
where the AI picks the way by its name. The model call is one seam (aistep._call), replaced here by a scripted fake.
"""
import asyncio
import json
import shutil
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_tools as D
from app.agent.tools import HANDLERS, Ctx, ToolError
from app.route import aistep as AS


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def _save(t, name, steps, **kw):
    return _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name=name, steps=steps, **kw))


def _go(t, name, vars_=None):
    rid = D.create_run(t, D.get_workflow(t, name=name), vars_=vars_)
    _run(D.execute_run(t, rid))
    return D.get_run(t, rid)


class Fake:
    """A scripted model: each call returns the next answer (text, or a dict = JSON, or ('tool', name, input))."""
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    async def __call__(self, system, messages, tools=None, max_tokens=1500, quality="fast"):
        self.calls.append({"system": system, "messages": json.loads(json.dumps(messages, default=str)), "tools": tools, "quality": quality})
        a = self.answers.pop(0) if self.answers else "done"
        if isinstance(a, tuple) and a[0] == "tool":
            return [{"type": "tool_use", "id": f"tu_{len(self.calls)}", "name": a[1], "input": a[2]}]
        return [{"type": "text", "text": a if isinstance(a, str) else json.dumps(a)}]


def test_ai_steps_are_checked_when_saved(bz):
    ok = [{"op": "write", "prompt": "hi"}, {"op": "summarise", "text": "x", "length": "points"},
          {"op": "classify", "text": "x", "categories": "a, b"}, {"op": "extract", "text": "x", "fields": {"name": "who"}},
          {"op": "sentiment", "text": "x"}, {"op": "answer", "question": "q", "knowledge": True},
          {"op": "agent", "prompt": "p", "tools": ["sheet_read"], "max_steps": 3}]
    for st in ok:
        AS.validate(st, "s")
    bad = [{"op": "dream"}, {"op": "write"}, {"op": "classify", "text": "x", "categories": "only"},
           {"op": "extract", "text": "x", "fields": {"bad name": 1}}, {"op": "answer", "question": "q"},
           {"op": "agent", "prompt": "p", "tools": ["dhara_run"]}, {"op": "agent", "prompt": "p", "tools": ["nope_tool"]},
           {"op": "agent", "prompt": "p", "max_steps": 50}, {"op": "summarise", "text": "x", "length": "huge"},
           {"op": "write", "prompt": "x", "quality": "magic"}]
    for st in bad:
        with pytest.raises(ToolError):
            AS.validate(st, "s")
    with pytest.raises(ToolError):
        D.validate_steps([{"id": "r", "type": "router", "ai": {}, "routes": [{"label": "A", "steps": [{"id": "x", "type": "set", "name": "a", "value": 1}]}]}])


def test_text_ops_check_the_answer_in_code(bz, monkeypatch):
    ctx = {"vars": {"msg": "My card 4111 1111 1111 1111 was charged twice, please refund!"}, "steps": {}}
    R = D.resolve
    fake = Fake({"category": "Complaint", "reason": "charged twice"})
    monkeypatch.setattr(AS, "_call", fake)
    out = _run(AS.run("t", {"op": "classify", "text": "{{vars.msg}}", "categories": "question, complaint, order"}, ctx, R))
    assert out == {"category": "complaint", "matched": True, "reason": "charged twice"}
    sent = fake.calls[0]["messages"][0]["content"]
    assert "<data>" in sent and "4111 1111 1111 1111" not in sent          # ID numbers masked before the AI reads them
    monkeypatch.setattr(AS, "_call", Fake({"category": "refund please"}))
    assert _run(AS.run("t", {"op": "classify", "text": "x", "categories": "question, order"}, ctx, R)) == \
        {"category": "", "matched": False, "reason": ""}                    # never a category she did not give
    monkeypatch.setattr(AS, "_call", Fake('```json\n{"name": "Ana", "amount": "1,250.50", "extra": "x"}\n```'))
    out = _run(AS.run("t", {"op": "extract", "text": "x", "fields": [{"name": "name"}, {"name": "amount", "type": "number"}, {"name": "date"}]}, ctx, R))
    assert out == {"name": "Ana", "amount": 1250.5, "date": None}           # exactly her fields, numbers as numbers
    monkeypatch.setattr(AS, "_call", Fake({"label": "Negative", "score": -3}))
    assert _run(AS.run("t", {"op": "sentiment", "text": "x"}, ctx, R)) == {"label": "negative", "score": -1.0, "reason": ""}
    f = Fake("A short summary.")
    monkeypatch.setattr(AS, "_call", f)
    assert _run(AS.run("t", {"op": "summarise", "text": "long", "length": "points", "language": "German", "quality": "best"}, ctx, R)) == {"summary": "A short summary."}
    assert "bullet points" in f.calls[0]["system"] and "German" in f.calls[0]["system"] and f.calls[0]["quality"] == "best"
    monkeypatch.setattr(AS, "_call", Fake("not json at all"))
    with pytest.raises(AS.AIError):
        _run(AS.run("t", {"op": "sentiment", "text": "x"}, ctx, R))


def test_answer_only_from_her_files(bz, monkeypatch):
    from app.agent import dhara_data as DD
    t = "r6_files"
    f = DD.run(t, {"op": "file", "action": "make_csv", "items": [{"plan": "Basic", "price": 9}], "name": "prices"}, {"vars": {}, "steps": {}}, D.resolve)
    fake = Fake("Basic costs 9 [prices.csv]", "NOT_IN_SOURCES")
    monkeypatch.setattr(AS, "_call", fake)
    ctx = {"vars": {"fid": f["file_id"]}, "steps": {}}
    out = _run(AS.run(t, {"op": "answer", "question": "Price of Basic?", "files": "{{vars.fid}}"}, ctx, D.resolve))
    assert out["found"] and "9" in out["answer"] and out["sources"] == ["prices.csv"]
    assert "Basic" in fake.calls[0]["messages"][0]["content"] and "ONLY from the sources" in fake.calls[0]["system"]
    out = _run(AS.run(t, {"op": "answer", "question": "Opening hours?", "text": "We sell plans."}, ctx, D.resolve))
    assert out == {"answer": "The files do not say.", "found": False, "sources": ["the text given"]}


def test_agent_uses_only_her_tools_and_remembers(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r6_agent"
    _wipe(t)
    seen = []

    async def stock(ctx, sku="", **kw):
        seen.append((ctx.actor, sku))
        return {"sku": sku, "left": 3}
    monkeypatch.setitem(HANDLERS, "route_test_stock_read", stock)
    from app.agent import tools as T
    monkeypatch.setattr(T, "TOOLS", T.TOOLS + [{"name": "route_test_stock_read", "description": "Stock left for a sku",
                                                 "input_schema": {"type": "object", "properties": {"sku": {"type": "string"}}}}])
    try:
        _save(t, "stock_agent", [{"id": "ask", "type": "ai", "op": "agent", "prompt": "How many {{vars.sku}} are left?",
                                  "tools": ["route_test_stock_read"], "max_steps": 4, "memory": "on", "memory_key": "{{vars.who}}"}])
        fake = Fake(("tool", "email_bulk", {"to": "everyone"}), ("tool", "route_test_stock_read", {"sku": "A1"}), "3 are left.")
        monkeypatch.setattr(AS, "_call", fake)
        r = _go(t, "stock_agent", {"sku": "A1", "who": "ana"})
        assert r["status"] == "done", r.get("error")
        out = r["context"]["steps"]["ask"]["output"]
        assert out["answer"] == "3 are left." and out["used"] == [{"tool": "email_bulk", "ok": False}, {"tool": "route_test_stock_read", "ok": True}]
        assert seen == [("routine", "A1")]                                   # only her tool ran, as a background routine
        assert [x["name"] for x in fake.calls[0]["tools"]] == ["route_test_stock_read"]
        refused = fake.calls[1]["messages"][-1]["content"][0]
        assert refused["is_error"] and "not one of the tools" in refused["content"]
        fake2 = Fake("Still 3.")
        monkeypatch.setattr(AS, "_call", fake2)
        _go(t, "stock_agent", {"sku": "A1", "who": "ana"})
        first = fake2.calls[0]["messages"]
        assert first[0] == {"role": "user", "content": "How many A1 are left?"} and first[1]["content"] == "3 are left."
        fake3 = Fake("Hi.")
        monkeypatch.setattr(AS, "_call", fake3)
        _go(t, "stock_agent", {"sku": "B2", "who": "raj"})
        assert len(fake3.calls[0]["messages"]) == 1                          # another person, another memory
        # out of steps: it answers with what it has
        fake4 = Fake(*[("tool", "route_test_stock_read", {"sku": "A1"})] * 4, "Ran out, 3 left.")
        monkeypatch.setattr(AS, "_call", fake4)
        r = _go(t, "stock_agent", {"sku": "A1", "who": "zed"})
        assert r["context"]["steps"]["ask"]["output"]["answer"] == "Ran out, 3 left." and fake4.calls[-1]["tools"] is None
    finally:
        _wipe(t)


def test_ai_picks_the_way_on_a_switch(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r6_switch"
    _wipe(t)
    try:
        _save(t, "triage", [{"id": "sort", "type": "router", "ai": {"text": "{{vars.message}}"},
                             "routes": [{"label": "Sales", "steps": [{"id": "s", "type": "set", "name": "went", "value": "sales"}]},
                                        {"label": "Support", "steps": [{"id": "h", "type": "set", "name": "went", "value": "support"}]}],
                             "fallback": [{"id": "f", "type": "set", "name": "went", "value": "other"}]}])
        monkeypatch.setattr(AS, "_call", Fake({"way": "support", "reason": "a problem"}))
        r = _go(t, "triage", {"message": "My order arrived broken"})
        assert r["context"]["vars"]["went"] == "support"
        assert r["context"]["steps"]["sort"]["output"] == {"routes": ["Support"], "why": "a problem"}
        monkeypatch.setattr(AS, "_call", Fake({"way": "none"}))
        assert _go(t, "triage", {"message": "hello"})["context"]["vars"]["went"] == "other"
        # a failed AI call fails the step honestly
        async def dead(*a, **k):
            raise AS.AIError("No AI model is set up on this server")
        monkeypatch.setattr(AS, "_call", dead)
        r = _go(t, "triage", {"message": "x"})
        assert r["status"] == "failed" and "No AI model" in r["error"]
    finally:
        _wipe(t)


def test_a_route_with_ai_steps_runs_end_to_end(bz, monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    t = "r6_flow"
    _wipe(t)
    try:
        _save(t, "inbox_helper", [
            {"id": "kind", "type": "ai", "op": "classify", "text": "{{vars.mail}}", "categories": "invoice, other"},
            {"id": "is_invoice", "type": "condition", "filter": {"left": "{{steps.kind.output.category}}", "op": "eq", "right": "invoice"},
             "then": [{"id": "pull", "type": "ai", "op": "extract", "text": "{{vars.mail}}", "fields": {"total": "the total", "due": "due date"}},
                      {"id": "keep", "type": "set", "name": "total", "value": "{{steps.pull.output.total}}"}]}])
        monkeypatch.setattr(AS, "_call", Fake({"category": "invoice"}, {"total": 120, "due": "2030-01-05"}))
        r = _go(t, "inbox_helper", {"mail": "Invoice 7, total 120, due 5 Jan 2030"})
        assert r["status"] == "done" and r["context"]["vars"]["total"] == 120
    finally:
        _wipe(t)


def test_page_and_catalog_know_the_ai_steps(bz):
    from app.route import editor as E
    keys = {k["key"]: k for k in E.KINDS}
    assert {"ai_agent", "ai_write", "ai_summarise", "ai_classify", "ai_extract", "ai_sentiment", "ai_answer", "ai_switch"} <= set(keys)
    assert all(keys[k]["group"] == "AI" for k in keys if k.startswith("ai_"))
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.js").read_text()
    for part in ("AIF", "AIW", "Let AI pick the way", "Answer from my files", "AI agent", "Tools it may use", "k-ai"):
        assert part in js, part
    assert "AI steps" in (Path(__file__).resolve().parents[1] / "app" / "route" / "chat.py").read_text()


# ---------------------------------------------------------------- a real browser
@pytest.fixture
def br6(bz, monkeypatch):
    import os
    import threading
    import time
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    _save(t, "ai_route", [{"id": "first", "type": "set", "name": "mail", "value": "Hello, my parcel is late"}])
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


def test_add_an_ai_step_in_a_real_browser(br6):
    base, b, key, t = br6
    wf = D.get_workflow(t, name="ai_route")
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(base + "#/r/" + wf["id"])
    p.wait_for_selector(".nd[data-node='first']")
    p.click(".nd[data-node='first'] .addaf", force=True)
    p.fill("#addQ", "categories")
    p.wait_for_selector("#addList .arow[data-kind='ai_classify']")
    p.click("#addList .arow[data-kind='ai_classify']")
    p.wait_for_selector("#edPanel [data-k='d:text']")
    p.fill("#edPanel [data-k='d:text']", "{{vars.mail}}")
    p.fill("#edPanel [data-k='d:categories']", "late parcel, refund, other")
    p.select_option("#edPanel [data-k='d:quality']", "best")
    p.click("#edSave")
    p.wait_for_function("() => document.querySelector('#edState').innerText === 'Saved'", timeout=10000)
    st = D.get_workflow(t, wf_id=wf["id"])["steps"][1]
    assert st["type"] == "ai" and st["op"] == "classify" and st["categories"] == "late parcel, refund, other" and st["quality"] == "best"
    assert "Sort into categories" in p.inner_text("#world")
    assert not errs, errs


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION >= "0.999.243"
