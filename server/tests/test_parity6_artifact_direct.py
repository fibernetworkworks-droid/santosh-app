"""parity Phase 6 - artifacts the Claude way (docs/CLAUDE_PARITY_PLAN.md, gap 9b): the chat model writes the page
itself in the `artifact` tool call (create / update old_str -> new_str / rewrite), every change a new version, the
page grows in the console panel while the call streams (artifact_draft), Undo in the panel; artifact_make (the
separate 16k builder) stays as the polish path. Setting chat_artifact_direct (default on; conftest pins it off for
the older suites, so these tests switch it back on)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

CON = Path(__file__).resolve().parents[1] / "app/static/console"
PAGE = ("<!doctype html><html><head><title>Milk</title><style>h1{color:red}</style></head><body>"
        "<h1>Milk tracker</h1><p>Rate 60</p><p>Days 30</p></body></html>")


@pytest.fixture()
def direct(env, monkeypatch):
    from app.config import get_settings
    monkeypatch.delenv("CHAT_ARTIFACT_DIRECT", raising=False)
    get_settings.cache_clear()
    from app.events import bus
    seen: list = []
    monkeypatch.setattr(bus, "publish", lambda c, k, p: seen.append((c, k, dict(p))))
    yield seen
    get_settings.cache_clear()


def _cards(seen):
    return [p for _c, k, p in seen if k == "artifact"]


def test_default_is_on(direct):
    from app.config import get_settings
    assert get_settings().chat_artifact_direct is True


def test_create_stores_v1_and_says_ready(direct):
    from app import artifacts
    r = artifacts.write("t1", "c1", "create", title="Milk tracker", kind="html", content=PAGE)
    assert r["version"] == 1 and r["status"] == "ready" and r["kind"] == "html"
    cards = _cards(direct)
    assert cards[0]["stage"] == "writing" and cards[0]["status"] == "building"     # the card shows Writing at once
    assert cards[-1]["status"] == "ready" and cards[-1]["stage"] == "done" and cards[-1]["version"] == 1
    assert cards[-1]["build_s"] is not None and cards[-1]["started_at"]
    assert artifacts.latest_html(r["id"]) == PAGE
    assert artifacts.current_source(r["id"]) == (1, "html", PAGE)


def test_update_changes_only_the_matched_text(direct):
    from app import artifacts
    a = artifacts.write("t1", "c1", "create", title="Milk", content=PAGE)
    r = artifacts.write("t1", "c1", "update", artifact_id=a["id"], edits=[{"old_str": "color:red", "new_str": "color:blue"}])
    assert r["version"] == 2
    v2 = artifacts.latest_html(a["id"])
    assert v2 == PAGE.replace("color:red", "color:blue")
    assert artifacts.latest_html(a["id"], 1) == PAGE                                  # v1 kept as it was
    r = artifacts.write("t1", "c1", "update", artifact_id=a["id"],
                        edits=[{"old_str": "Rate 60", "new_str": "Rate 62"}, {"old_str": "Days 30", "new_str": "Days 31"}])
    assert r["version"] == 3 and "Rate 62" in artifacts.latest_html(a["id"]) and "Days 31" in artifacts.latest_html(a["id"])


def test_missing_or_duplicate_old_str_is_refused_clearly(direct):
    from app import artifacts
    a = artifacts.write("t1", "c1", "create", title="Milk", content=PAGE)
    with pytest.raises(artifacts.EditError) as e:
        artifacts.write("t1", "c1", "update", artifact_id=a["id"], edits=[{"old_str": "Rate 99", "new_str": "x"}])
    assert "not found in v1 of 'Milk'" in str(e.value) and "Rate 99" in str(e.value)
    with pytest.raises(artifacts.EditError) as e:
        artifacts.write("t1", "c1", "update", artifact_id=a["id"], edits=[{"old_str": "<p>", "new_str": "<p class=x>"}])
    assert "occurs 2 times" in str(e.value)
    with pytest.raises(artifacts.EditError):   # all or none: the first edit fits, the second does not
        artifacts.write("t1", "c1", "update", artifact_id=a["id"],
                        edits=[{"old_str": "Rate 60", "new_str": "Rate 61"}, {"old_str": "nope", "new_str": "x"}])
    assert artifacts.get("t1", a["id"]).version == 1 and artifacts.latest_html(a["id"]) == PAGE


def test_rewrite_makes_the_next_version(direct):
    from app import artifacts
    a = artifacts.write("t1", "c1", "create", title="Milk", content=PAGE)
    artifacts.write("t1", "c1", "update", artifact_id=a["id"], edits=[{"old_str": "Rate 60", "new_str": "Rate 61"}])
    new = PAGE.replace("Milk tracker", "Doodh hisaab")
    r = artifacts.write("t1", "c1", "rewrite", artifact_id=a["id"], content=new)
    assert r["version"] == 3 and artifacts.latest_html(a["id"]) == new
    d = artifacts.detail("t1", a["id"])
    assert [v["version"] for v in d["versions"]] == [3, 2, 1] and all(v["direct"] for v in d["versions"])


def test_html_is_cleaned_like_the_builder(direct):
    from app import artifacts
    r = artifacts.write("t1", "c1", "create", title="X", content="Here it is:\n```html\n" + PAGE + "\n```")
    assert artifacts.latest_html(r["id"]) == PAGE                    # fences + chatter before the doctype go
    r = artifacts.write("t1", "c1", "create", title="Frag <b>", content="<h1>Only a fragment</h1>")
    page = artifacts.latest_html(r["id"])
    assert page.startswith("<!doctype html>") and "<h1>Only a fragment</h1>" in page and "Frag &lt;b&gt;" in page
    with pytest.raises(artifacts.EditError):
        artifacts.write("t1", "c1", "create", title="Big", content="<p>" + "x" * (artifacts.MAX_HTML + 10) + "</p>")
    with pytest.raises(artifacts.EditError):
        artifacts.write("t1", "c1", "create", title="Empty", content="   ")
    # the served page is the same sandboxed CSP + bridge as every page
    html = artifacts.render(r["id"], 1, page)
    assert "window.santosh" in html and "sandbox" in artifacts.headers()["Content-Security-Policy"]


def test_markdown_svg_mermaid_are_wrapped_and_edit_their_own_text(direct):
    from app import artifacts
    md = artifacts.write("t1", "c1", "create", title="Plan", kind="markdown", content="# Plan\n\n- <b>buy</b> milk")
    page = artifacts.latest_html(md["id"])
    assert artifacts.MARKED_JS in page and "&lt;b&gt;buy&lt;/b&gt;" in page
    r = artifacts.write("t1", "c1", "update", artifact_id=md["id"],
                        edits=[{"old_str": "milk", "new_str": "curd"}])
    assert r["kind"] == "markdown" and artifacts.current_source(md["id"])[2] == "# Plan\n\n- <b>buy</b> curd"
    sv = artifacts.write("t1", "c1", "create", title="Logo", kind="svg", content='<svg viewBox="0 0 10 10"><circle r="4"/></svg>')
    assert "<svg viewBox" in artifacts.latest_html(sv["id"])
    with pytest.raises(artifacts.EditError):
        artifacts.write("t1", "c1", "create", title="No", kind="svg", content="<div>not svg</div>")
    mm = artifacts.write("t1", "c1", "create", title="Flow", kind="mermaid", content="graph TD; A-->B")
    assert artifacts.MERMAID_JS in artifacts.latest_html(mm["id"]) and "A--&gt;B" in artifacts.latest_html(mm["id"])
    with pytest.raises(artifacts.EditError):
        artifacts.write("t1", "c1", "create", title="?", kind="react", content="x")


def test_tenant_isolation(direct):
    from app import artifacts
    a = artifacts.write("t1", "c1", "create", title="Mine", content=PAGE)
    with pytest.raises(artifacts.EditError) as e:
        artifacts.write("t2", "c9", "update", artifact_id=a["id"], edits=[{"old_str": "Rate 60", "new_str": "Rate 0"}])
    assert "wasn't found" in str(e.value)
    with pytest.raises(artifacts.EditError):
        artifacts.write("t2", "c9", "rewrite", artifact_id=a["id"], content=PAGE)
    assert artifacts.undo("t2", a["id"]) is None
    assert artifacts.get("t1", a["id"]).version == 1 and artifacts.list_for("t2") == []


def test_undo_brings_the_version_before_back_as_a_new_one(direct):
    from app import artifacts
    a = artifacts.write("t1", "c1", "create", title="Milk", content=PAGE)
    with pytest.raises(artifacts.EditError):
        artifacts.undo("t1", a["id"])
    artifacts.write("t1", "c1", "update", artifact_id=a["id"], edits=[{"old_str": "Rate 60", "new_str": "Rate 61"}])
    r = artifacts.undo("t1", a["id"])
    assert r["version"] == 3 and artifacts.latest_html(a["id"]) == PAGE
    assert artifacts.detail("t1", a["id"])["versions"][0]["note"] == "Undo: back to v1"


def test_the_tool(direct):
    from app import artifacts
    from app.agent import tools as T
    from app.agent.artifact_tools import artifact
    from app.agent.tools import Ctx, ToolError
    assert "artifact" in T.HANDLERS and "artifact_make" in T.HANDLERS and T.FAMILY_OF["artifact"] == "artifact"
    spec = next(t for t in T.TOOLS if t["name"] == "artifact")
    assert set(spec["input_schema"]["properties"]["action"]["enum"]) == {"create", "update", "rewrite"}
    assert "studio-quality page she asked for -> artifact_make" in spec["description"]
    mk = next(t for t in T.TOOLS if t["name"] == "artifact_make")
    assert "POLISH builder" in mk["description"] and "-> artifact." in mk["description"]
    ctx = Ctx("t1", "c1")
    r = asyncio.run(artifact(ctx, action="create", title="Milk", type="html", content=PAGE))
    assert r["version"] == 1 and "Open button" in r["say"]
    r = asyncio.run(artifact(ctx, action="update", artifact_id=r["id"], old_str="Rate 60", new_str="Rate 65"))
    assert r["version"] == 2 and "Rate 65" in artifacts.latest_html(r["id"])
    with pytest.raises(ToolError) as e:
        asyncio.run(artifact(ctx, action="update", artifact_id=r["id"], old_str="Rate 60", new_str="x"))
    assert "not found" in str(e.value)
    with pytest.raises(ToolError):
        asyncio.run(artifact(ctx, action="delete", artifact_id=r["id"]))


def test_switch_off_refuses_and_keeps_the_old_prompt(env, monkeypatch):
    from app.agent import prompts
    from app.agent.artifact_tools import artifact
    from app.agent.tools import Ctx, ToolError
    with pytest.raises(ToolError) as e:   # conftest pins the switch off
        asyncio.run(artifact(Ctx("t1", "c1"), action="create", content=PAGE))
    assert "artifact_make" in str(e.value)
    off = prompts.system_text()
    assert "call artifact_make with a complete brief" in off and "WRITE it yourself" not in off
    from app.config import get_settings
    monkeypatch.delenv("CHAT_ARTIFACT_DIRECT", raising=False)
    get_settings.cache_clear()
    on = prompts.system_text()
    assert "WRITE it yourself with the artifact tool" in on and "action=update with the exact old_str" in on


def test_old_builder_path_still_works(direct, monkeypatch):
    from app import artifacts

    async def fake_llm(system, prompt, max_tokens=16000):
        return "TITLE: EMI\nSUMMARY: calc\n" + PAGE.replace("</body>", "<p>pad</p>" * 30 + "</body>")
    monkeypatch.setattr(artifacts, "_llm", fake_llm)
    r = asyncio.run(artifacts.make("t1", "c1", "EMI calculator banao", wait=5))
    assert r["status"] == "ready" and r["version"] == 1 and r["title"] == "EMI"
    # a builder page can then be edited directly (its source = its HTML)
    r2 = artifacts.write("t1", "c1", "update", artifact_id=r["id"], edits=[{"old_str": "Rate 60", "new_str": "Rate 70"}])
    assert r2["version"] == 2 and "Rate 70" in artifacts.latest_html(r["id"])


def test_partial_tool_args_become_a_live_draft(direct, monkeypatch):
    from app import livereply
    from app.events import STREAM_KINDS, bus
    assert "artifact_draft" in STREAM_KINDS                 # live-only, never stored
    d = livereply.draft_fields('{"action": "create", "title": "Mi\\u006ck", "type": "html", "content": "<h1>Hi \\"you\\"\\nline')
    assert d == {"action": "create", "title": "Milk", "type": "html", "content": '<h1>Hi "you"\nline'}
    assert livereply.draft_fields('{"title": "Half') == {}  # a short field only when complete
    assert livereply.draft_fields('{"content": "ab\\') == {"content": "ab"}     # an escape cut in half waits
    live = []
    monkeypatch.setattr(bus, "publish_live", lambda c, k, p: live.append((c, k, p)))
    lv = livereply.Live("c1", "t1")
    lv.feed_tool(0, "artifact", '{"action": "create", "title": "Milk", "content": "<!doctype html><h1>Mi')
    lv.feed_tool(0, "artifact", '{"action": "create", "title": "Milk", "content": "<!doctype html><h1>Milk')   # throttled
    lv.feed_tool(1, "artifact", '{"action": "update", "artifact_id": "a1", "old_str": "x"')                    # an edit: no draft
    lv.feed_tool(2, "google_search", '{"q": "x"}')                                                             # other tools: none
    assert [k for _c, k, _p in live] == ["artifact_draft"]
    p = live[0][2]
    assert p["title"] == "Milk" and p["text"] == "<!doctype html><h1>Mi" and p["chars"] == 21 and p["turn"] == lv.turn


def test_claude_stream_feeds_the_tool_args(direct):
    from app.agent import santosh

    class Ev:
        def __init__(self, **k):
            self.__dict__.update(k)

    class D:
        def __init__(self, **k):
            self.__dict__.update(k)

    evs = [Ev(type="content_block_start", index=0, content_block=D(type="tool_use", name="artifact")),
           Ev(type="content_block_delta", index=0, delta=D(type="input_json_delta", partial_json='{"content": "<h1')),
           Ev(type="content_block_delta", index=0, delta=D(type="input_json_delta", partial_json='>Hi"}'))]

    class Msg:
        content, stop_reason, usage = [], "tool_use", None

    class St:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def __aiter__(self):
            async def g():
                for e in evs:
                    yield e
            return g()

        async def get_final_message(self):
            return Msg()

    class Api:
        def stream(self, **kw):
            return St()

    got = []

    class L(santosh._QuietLive):
        def feed_tool(self, i, name, args):
            got.append((i, name, args))
    asyncio.run(santosh._claude_stream(Api(), {"model": "x", "messages": []}, L()))
    assert got == [(0, "artifact", '{"content": "<h1'), (0, "artifact", '{"content": "<h1>Hi"}')]


def test_console_draws_draft_undo_and_source():
    pj, vj = (CON / "panel.js").read_text(), (CON / "v2.js").read_text()
    assert "function draft(p)" in pj and "return {itemOf, open, update, draft," in pj
    assert "f.setAttribute('sandbox', '')" in pj                    # a draft runs no scripts
    assert 'data-a="undo"' in pj and "/undo`" in pj
    assert "s.source ?? s.html" in pj                              # Code shows what was written
    assert "case 'artifact_draft':" in vj and "'artifact_draft'" in vj.split("const LOCAL = new Set(")[1][:200]
    assert "p.draft ?" in vj                                        # the draft card: size so far, no Stop


def test_undo_and_source_routes(direct):
    from fastapi.testclient import TestClient
    from app import artifacts
    from app.main import app
    a = artifacts.write("default", "c1", "create", title="Plan", kind="markdown", content="# A\n\nb")
    artifacts.write("default", "c1", "update", artifact_id=a["id"], edits=[{"old_str": "b", "new_str": "c"}])
    c = TestClient(app)
    s = c.get(f"/api/panel/pages/{a['id']}/source?version=2")
    if s.status_code == 200:   # the panel is on in this config
        assert s.json()["kind"] == "markdown" and s.json()["source"] == "# A\n\nc"
    r = c.post(f"/api/artifacts/{a['id']}/undo")
    assert r.status_code == 200 and r.json()["version"] == 3
    assert artifacts.current_source(a["id"])[2] == "# A\n\nb"
    assert c.post("/api/artifacts/nope/undo").status_code == 404
