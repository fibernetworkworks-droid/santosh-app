"""v0.772 HOOLA AI APPS D - the console page (static checks) and the `ai_app` agent tool (publish_card never publishes)."""
import asyncio
import re
from pathlib import Path

CONSOLE = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
JS = CONSOLE / "aiapps.js"

# every route the console must call, exactly as docs/AIAPPS_PLAN.md writes them (with this file's template parts)
ROUTES = [
    "'GET', B)", "'POST', B, {",                                  # GET / POST /api/aiapps
    "`${B}/plan`", "`${B}/${q(id)}`", "`${B}/${q(APP.id)}/draft`", "`${B}/${q(a.id)}/publish`",
    "`${B}/${q(APP.id)}/versions`", "`${B}/${q(APP.id)}/restore`", "`${B}/${q(APP.id)}/status`",
    "`${B}/${q(a.id)}/channels`", "'DELETE', `${B}/${q(APP.id)}`", "`${B}/${q(APP.id)}/preview`",
    "`${B}/${q(APP.id)}/logs?outcome=", "`${B}/${q(APP.id)}/logs/${q(m.id)}/correct`",
    "`${B}/${q(APP.id)}/stats?days=", "`${B}/${q(APP.id)}/gaps`",
    "`${B}/${q(APP.id)}/keys`", "`${B}/${q(APP.id)}/keys/${q(k.id)}`",
    "`${B}/templates?q=", "`${B}/templates/${q(t.key)}/trial`", "`${B}/templates/${q(t.key)}/use`",
    "/ai/${a.code}", "/ai/${a.code}/embed.js", "/mcp/aiapp/${a.code}",
]


def test_page_exists_and_uses_every_contract_route():
    s = JS.read_text()
    assert "const B = '/api/aiapps'" in s
    for r in ROUTES:
        assert r in s, r
    assert "{hash: a.draft_hash" in s                              # publish is bound to the hash she saw
    assert "window.HoolaAiApps = function" in s
    assert (CONSOLE / "aiapps.css").exists()


def test_no_innerhtml_with_server_data():
    s = JS.read_text()
    assert not re.search(r"\.innerHTML\s*=", s), "aiapps.js builds every node with textContent"
    assert not re.search(r"insertAdjacentHTML|outerHTML\s*=|document\.write", s)


def test_css_uses_console_tokens_only():
    css = (CONSOLE / "aiapps.css").read_text()
    bare = [c for c in re.findall(r"#[0-9a-fA-F]{3,8}\b", css) if c.lower() not in ("#fff",)]
    assert not bare, bare                                        # the QR keeps a white ground; everything else is a token
    assert "var(--ink)" in css and "var(--pri)" in css


def test_v2_html_and_sidebar_row():
    html = (CONSOLE / "v2.html").read_text()
    stamps = {m for m in re.findall(r'console/[a-z0-9]+\.(?:js|css)\?v=([0-9.]+)', html)}
    assert len(stamps) == 1                                      # the same stamp as its neighbours
    assert f'src="/static/console/aiapps.js?v={stamps.pop()}"' in html
    assert 'aiapps.css' not in html                              # v2.html keeps ONE stylesheet; aiapps.js loads its own
    assert "/static/console/aiapps.css" in JS.read_text() and 'id="v-aiapps"' in html and 'id="aiapps"' in html
    v2 = (CONSOLE / "v2.js").read_text()
    assert "['aiapps', 'AI Apps']" in v2 and "HoolaAiApps({api, esc, toast})" in v2
    assert "AIA?.open($('#aiapps'), arg)" in v2 and "AIA?.leave()" in v2 and "IC.aiapps" in v2


def _ctx(tenant="t1", actor="owner"):
    from app.agent.tools import Ctx
    return Ctx(tenant_id=tenant, conversation_id="", actor=actor)


def _run(coro):
    return asyncio.run(coro)


def test_tool_shape():
    from app.agent import aiapp_tools as T
    assert [t["name"] for t in T.AIAPP_TOOLS] == ["ai_app"]
    assert set(T.AIAPP_HANDLERS) == {"ai_app"} == set(T.AIAPP_LABELS)
    enum = T.AIAPP_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    assert enum == ["list", "show", "plan", "create", "preview", "publish_card", "logs", "stats"]


def test_publish_card_never_publishes(env):
    from app.agent import aiapp_tools as T
    from app.aiapps import runtime as RT
    from app.aiapps import store as ST
    h = T.AIAPP_HANDLERS["ai_app"]
    made = _run(h(_ctx(), "create", name="Sharma Kirana",
                  soul={"name": "Sharma Kirana", "about": "Grocery shop", "facts": ["Open 9 am to 9 pm"]}))
    aid = made["id"]
    assert made["status"] == "draft" and made["live_version"] == 0
    card = _run(h(_ctx(), "publish_card", app=aid, note="first"))
    assert card["kind"] == "aiapp_publish" and card["app_id"] == aid and card["version_to_be"] == 1
    assert card["hash"] == made["draft_hash"] and "your tap" in card["says"]
    a = ST.row("t1", aid)
    assert a.status == "draft" and a.live_version == 0 and ST.versions("t1", aid) == []
    # after a real publish (her tap) a second card still changes nothing
    ST.publish("t1", aid, card["hash"])
    soul = ST.get("t1", aid)["draft"]
    soul["facts"] = soul["facts"] + ["Delivery free above Rs 500"]
    ST.save_draft("t1", aid, soul)
    card2 = _run(h(_ctx(), "publish_card", app=aid))
    a2 = ST.row("t1", aid)
    assert a2.live_version == 1 and a2.status == "live" and len(ST.versions("t1", aid)) == 1
    assert card2["version_to_be"] == 2 and any(c.startswith("facts") for c in card2["changes"])
    # preview answers from the draft on the private channel, stats / logs read it back
    RT.ASK[0] = lambda s, p, n: "Delivery free above Rs 500"
    try:
        pv = _run(h(_ctx(), "preview", app=aid, text="Is delivery free?"))
    finally:
        RT.ASK[0] = RT._ask_model
    assert pv["outcome"] == "model" and pv["session_id"]
    logs = _run(h(_ctx(), "logs", app=aid))
    assert logs["items"] and logs["items"][0]["channel"] == "preview"
    st = _run(h(_ctx(), "stats", app=aid))
    assert isinstance(st, dict)
    assert [x["id"] for x in _run(h(_ctx(), "list"))["apps"]] == [aid]


def test_tool_refuses_customers_and_bad_actions(env):
    import pytest
    from app.agent import aiapp_tools as T
    from app.agent.tools import ToolError
    h = T.AIAPP_HANDLERS["ai_app"]
    with pytest.raises(ToolError):
        _run(h(_ctx(actor="customer:c1"), "list"))
    with pytest.raises(ToolError):
        _run(h(_ctx(), "fly"))
    with pytest.raises(ToolError):
        _run(h(_ctx(), "show", app="aia_nope"))
    with pytest.raises(ToolError):
        _run(h(_ctx(), "plan", words=""))


def test_numbers_read_the_totals_and_no_null_child():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "aiapps.js").read_text()
    assert "st.totals" in js and "No ratings yet" in js           # the stats route answers {totals, per_day, says}
    assert "].filter(Boolean))" in js                             # replaceChildren(null) printed the word 'null'
