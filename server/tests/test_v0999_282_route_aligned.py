"""v0.999.282 EVERY PAGE ALIGNED (owner: "NOW GO DEEP ON EVERY PAGE OF ROUTE AND ALINE AND MAKE EVERY SECTION PERFCTLY FIXED").

Every Route page is opened in a real browser with a realistic account (routes of every start, runs that went well / failed /
wait, a data store, variables, sign-ins, a library workflow) at computer and phone width, light and dark, and measured:
nothing scrolls sideways, nothing sticks out of the page, no text is cut, controls side by side share a height and a middle
line, no control is smaller than 26 px, and no page throws an error. Plus the rules that fixed what the walk found.
"""
import asyncio
import os
import threading
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401

from app.agent import dhara_tools as D
from app.agent.tools import Ctx

CSS = Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.css"
JS = Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "route.js"

MEASURE = r"""
() => {
  const vw = document.documentElement.clientWidth, out = {sideways: document.documentElement.scrollWidth - vw, over: [], clip: [], rows: [], tiny: []};
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const name = e => (e.id ? '#' + e.id : '') + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/).slice(0, 3).join('.') : '') + '<' + e.tagName.toLowerCase() + '>' + (e.innerText || e.value || '').trim().slice(0, 30).replace(/\s+/g, ' ');
  const all = [...document.querySelectorAll('#main *, .side *, body > *')];
  for (const e of all) {
    if (!vis(e)) continue;
    const r = e.getBoundingClientRect();
    if (r.right > vw + 1 && !e.closest('.canvas,.world,.tw,.mini,[data-scroll],.segtabs,.chips,.libtools,.gridwrap,.side')) out.over.push(name(e) + ' right=' + Math.round(r.right));
    const s = getComputedStyle(e);
    if (e.children.length === 0 && (e.innerText || '').trim() && e.scrollWidth > e.clientWidth + 2 && s.overflowX !== 'visible' && s.textOverflow !== 'ellipsis' && !['INPUT','TEXTAREA','SELECT'].includes(e.tagName))
      out.clip.push(name(e));
    if (['BUTTON','A','INPUT','SELECT'].includes(e.tagName) && (e.classList.contains('btn') || ['INPUT','SELECT'].includes(e.tagName)) && r.height < 26 && !e.closest('.srch') && !['checkbox','radio','range','hidden','file'].includes(e.type)) out.tiny.push(name(e) + ' h=' + Math.round(r.height));
  }
  // rows of controls: buttons / inputs / selects side by side should share a height and a middle line
  for (const row of document.querySelectorAll('#main .crow, #main .two, #main .libbar, #main .libtools, #main .top, #main .rhead, #main .edtop, #main .phead, #main .tf, #main .hd, #main .lrow, #main .bar, #main .toolbar, #main .sendbar, #main form')) {
    if (!vis(row)) continue;
    const kids = [...row.children].filter(k => vis(k) && /^(BUTTON|A|SELECT|INPUT|LABEL)$/.test(k.tagName) && (k.classList.contains('btn') || k.tagName !== 'A'));
    if (kids.length < 2) continue;
    const lines = {};
    for (const k of kids) { const r = k.getBoundingClientRect(); const key = Math.round(r.top / 6); (lines[key] = lines[key] || []).push([k, r]); }
    for (const g of Object.values(lines)) {
      if (g.length < 2) continue;
      const hs = g.map(([, r]) => Math.round(r.height)), mids = g.map(([, r]) => Math.round(r.top + r.height / 2));
      if (Math.max(...hs) - Math.min(...hs) > 2 || Math.max(...mids) - Math.min(...mids) > 2) out.rows.push(name(row) + ' h=' + hs.join('/') + ' mid=' + mids.join('/'));
    }
  }
  out.over = [...new Set(out.over)].slice(0, 12); out.clip = [...new Set(out.clip)].slice(0, 12); out.rows = [...new Set(out.rows)].slice(0, 12); out.tiny = [...new Set(out.tiny)].slice(0, 12);
  return out;
}
"""


def _run(c):
    return asyncio.run(c)


def _save(t, name, steps, **kw):
    return _run(D.dhara_save(Ctx(tenant_id=t, conversation_id=""), name=name, steps=steps, **kw))


def _seed(t):
    from app.route import store as DS
    from app.route import workspace as WS
    big = [
        {"id": "read_orders", "type": "tool", "name": "sheet_read", "args": {"spreadsheet": "Orders", "tab": "June"}, "label": "Read the new orders"},
        {"id": "page", "type": "http", "method": "GET", "url": "https://api.example.com/items"},
        {"id": "big_one", "type": "condition", "filter": {"left": "{{vars.total}}", "op": "gt", "right": 500}, "label": "Is it a big order?",
         "then": [{"id": "ask", "type": "approval", "question": "A big order came in - go ahead?"}],
         "else": [{"id": "small", "type": "set", "name": "kind", "value": "small"}]},
        {"id": "each", "type": "loop", "items": "{{vars.items}}", "body": [{"id": "sum", "type": "data", "op": "aggregate", "items": "{{item}}", "field": "n", "how": "sum"}]},
        {"id": "pick", "type": "router", "routes": [{"label": "India", "filter": {"left": "{{vars.c}}", "op": "eq", "right": "IN"}, "steps": [{"id": "in1", "type": "notify", "text": "India"}]},
                                                    {"label": "World", "steps": [{"id": "w1", "type": "notify", "text": "World"}]}]},
        {"id": "summary", "type": "ai", "op": "summarise", "text": "{{steps.page.output}}", "length": "short"},
        {"id": "mail", "type": "send", "via": "email", "to": "boss@example.com", "subject": "Daily orders", "body": "{{steps.summary.output}}"},
        {"id": "tg", "type": "send", "via": "telegram", "chat": "123456", "text": "Orders are in"},
        {"id": "keep", "type": "store", "op": "add", "store": "customers", "key": "{{vars.email}}", "data": {"name": "{{vars.name}}"}},
        {"id": "pause", "type": "wait", "amount": 10, "unit": "minutes"},
        {"id": "tell", "type": "notify", "text": "Done for today"},
    ]
    _save(t, "daily_orders_with_a_long_name_that_goes_on_and_on", big, trigger="schedule", trigger_spec={"at": ["09:00"], "days": ["mon", "tue"]},
          settings={"folder": "Sales", "tags": ["orders", "daily"]})
    _save(t, "new_lead_form", [{"id": "thanks", "type": "respond", "status": 200, "body": {"ok": True}}], trigger="form",
          trigger_spec={"title": "Get a quote", "fields": [{"name": "name", "label": "Your name", "type": "text", "required": True}]},
          settings={"folder": "Sales"})
    _save(t, "support_chat", [{"id": "reply", "type": "respond", "status": 200, "body": "Hi"}], trigger="chat", trigger_spec={"greeting": "Hi!"})
    _save(t, "shop_webhook", [{"id": "a", "type": "set", "name": "x", "value": 1}], trigger="webhook")
    _save(t, "new_mail_alerts", [{"id": "a", "type": "notify", "text": "New mail"}], trigger="event",
          trigger_spec={"app": "email", "folder": "inbox", "every_minutes": 15})
    _save(t, "when_things_fail", [{"id": "a", "type": "notify", "text": "{{vars.error}}"}], trigger="error", trigger_spec={"routes": []})
    _save(t, "broken_route", [{"id": "boom", "type": "stop", "as": "error", "message": "The shop's site did not answer"}])
    _save(t, "needs_my_ok", [{"id": "ok", "type": "approval", "question": "Pay the supplier 12,000?"}, {"id": "b", "type": "notify", "text": "x"}])
    for n in ("shop_webhook", "broken_route", "needs_my_ok", "new_mail_alerts"):
        wf = D.get_workflow(t, name=n)
        D.set_enabled(t, wf["id"], True)
        for _ in range(2 if n != "needs_my_ok" else 1):
            rid = D.create_run(t, wf, vars_={"x": 1})
            _run(D.execute_run(t, rid))
    DS.save_store(t, "customers", [{"name": "name", "type": "text"}, {"name": "city", "type": "text"}])
    for i in range(6):
        DS.put(t, "customers", f"c{i}@example.com", {"name": f"Customer {i}", "city": "Pune"})
    WS.set_variable(t, "SHOP_NAME", "Asha Bakes", "Shown on mails")
    WS.save_credential(t, {"name": "SHOP_API", "kind": "bearer", "host": "api.example.com", "token": "tok_abcdef123456"})
    WS.save_credential(t, {"name": "MY_BOT", "kind": "telegram", "token": "123456789:AAH" + "x" * 32})



def test_the_rules_that_fixed_it():
    css, js = CSS.read_text(), JS.read_text()
    assert ".card > .pform,.card > form.pform{padding:0}" in css, "a form in a card is padded once"
    assert ".card.flat > .hd{padding:" in css, "a heading in a table card gets padding"
    assert "appearance:none" in css and "file-selector-button" in css, "drop-downs and file pickers have the house look"
    assert "table.rt td.c-act{text-align:right" in css and "td[data-l]::before{display:inline-block;min-width:92px" in css
    assert ".stat b{font-family:'Literata'" in css, "one number style on every page"
    assert ".edpage{margin:0 auto" in css and ".three{" in css
    assert "fit(true)" in js and "parseFloat(cs.paddingLeft" in js and "scrollIntoView" in js
    assert "Stopped at " in js and "toUpperCase()" in js


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_route_page_is_aligned(bz, monkeypatch, theme):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    from tests.test_v0999_264_workflow_library import _fake_lib
    from app.route import n8nlib as L
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    import shutil
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)
    _seed(t)
    big = D.get_workflow(t, name="daily_orders_with_a_long_name_that_goes_on_and_on")
    bad = D.get_workflow(t, name="broken_route")
    run_id = D.list_runs(t, bad["id"], 1)[0]["id"]
    real = L.index()
    row = _fake_lib(monkeypatch)
    monkeypatch.setattr(L, "_INDEX", {"source": L.SOURCE, "items": real["items"] + [row], "left_out": real.get("left_out", 0),
                                      "by_id": {**real["by_id"], row["id"]: row}})
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
    B = f"/r/{big['id']}"
    pages = [("home", "/", None), ("routes", "/routes", None), ("needs", "/needs", None), ("runs", "/runs", None),
             ("run", f"/run/{run_id}", None), ("insights", "/insights", None), ("import", "/import", None),
             ("templates", "/templates", None), ("workflows", "/workflows", None), ("variables", "/variables", None),
             ("signins", "/signins/telegram", None), ("stores", "/stores", None), ("store_one", "/stores/customers", None),
             ("grid", "/grid", None), ("editor", B, None), ("editor_step", B, ".nd[data-node='mail']"),
             ("editor_trigger", B, ".nd[data-node='trigger']"), ("editor_add", B, "#tAdd"),
             ("r_runs", B + "/runs", None), ("r_versions", B + "/versions", None), ("r_settings", B + "/settings", None),
             ("lib_one", f"/workflows/{row['id']}", None)]
    bad_pages = {}
    try:
        pw = sync_api.sync_playwright().start()
        try:
            b = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        try:
            for w in (1440, 390):
                c = b.new_context(viewport={"width": w, "height": 900 if w > 500 else 844}, color_scheme=theme)
                c.add_init_script(f"localStorage.setItem('hoola.console.token', '{KEY}')")
                p = c.new_page()
                errs = []
                p.on("pageerror", lambda e: errs.append(str(e)))
                for key, path, click in pages:
                    errs.clear()
                    p.goto(f"http://127.0.0.1:{port}/console/route#{path}")
                    try:
                        p.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:   # noqa: BLE001
                        pass
                    time.sleep(0.4)
                    if click:
                        p.click(click, timeout=5000)
                        time.sleep(0.5)
                    m = p.evaluate(MEASURE)
                    # the home's round send button (36) beside its 32 chips is on the same middle line by design
                    m["rows"] = [x for x in m["rows"] if "Start from a template" not in x]
                    if m["sideways"] > 0 or m["over"] or m["clip"] or m["rows"] or m["tiny"] or errs:
                        bad_pages[f"{key}@{w}"] = {**{k: m[k] for k in ("sideways", "over", "clip", "rows", "tiny")}, "errors": list(errs)}
                c.close()
        finally:
            b.close()
            pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)
        shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)
    assert not bad_pages, bad_pages


def test_version():
    from app.main import APP_VERSION
    assert tuple(int(x) for x in APP_VERSION.split(".")) >= (0, 999, 282)
