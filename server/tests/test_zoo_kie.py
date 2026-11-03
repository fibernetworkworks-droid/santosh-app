"""v0.463.1 ZOO kie tests: the kie.ai gateway inside the BYOK zoo (app/zoo.py + zoo_catalog.json).

Pins BOTH:
- the kie transport (createTask/recordInfo, Bearer key, "kie:"-prefixed request ids, CDN upload
  for local references, usage namespace zoo:kie:*) against a fake gateway - no real network;
- THE EXISTING CODEBASE STAYS INTACT: the 22 kie entries are purely appended (no muapi id
  collides, the muapi payload shape is unchanged), and curated studios stay byte-identical
  (test_zoo.py re-pins those on the same tree).
"""
import asyncio
import json

import pytest

from app import zoo
from app.zoo import ZooError
from app.agent.zoo_tools import zoo_tool
from app.agent.tools import Ctx, ToolError

CTX = Ctx(tenant_id="t1", conversation_id="c1")


# ------------------------------------------------------------------ catalog: the kie section
def test_kie_entries_shape():
    cat = zoo.load_catalog()
    ms = [m for m in cat["models"] if m.get("gateway") == "kie"]
    # v0.463.2: the 22 curated kie entries remain, the FULL kie.ai catalog (229 live models,
    # chat excluded) is appended after them - entries grow by appending, pins stay structural.
    assert len(ms) >= 22, f"expected the 22 curated kie entries + full-catalog additions, got {len(ms)}"
    assert cat["count"] == len(cat["models"]) >= 233
    ids = [m["id"] for m in cat["models"]]
    assert len(ids) == len(set(ids)), "kie ids must not collide with the muapi ones"
    for m in ms:
        assert m["endpoint"] and m["kind"] in ("image", "video", "audio") \
            and m["mode"] in ("t2i", "i2i", "t2v", "i2v", "v2v", "t2s", "t2m", "a2a")
    modes = {(m["kind"], m["mode"]) for m in ms}
    assert {("image", "t2i"), ("image", "i2i"), ("video", "t2v"), ("video", "i2v")} <= modes
    assert zoo.gateway_of(zoo.model("t2i:kie:nano-banana-2")) == "kie"
    assert zoo.gateway_of(zoo.model("t2i:nano-banana")) == "muapi"   # catalog root default untouched


def test_kie_params_come_from_the_entry_not_handwritten():
    p = zoo._payload(zoo.model("i2i:kie:nano-banana-pro"), "make the sky blue", ["https://a.example/1.jpg"])
    assert p["image_input"] == "https://a.example/1.jpg"             # nano-banana-pro's real param
    p2 = zoo._payload(zoo.model("i2i:kie:nano-banana-pro"), "sky",
                      ["https://a.example/1.jpg", "https://a.example/2.jpg"])
    assert p2["image_input"] == ["https://a.example/1.jpg", "https://a.example/2.jpg"]   # multi -> list param
    p3 = zoo._payload(zoo.model("i2i:kie:gpt-image-2-edit"), "bg white", ["https://a.example/1.jpg"])
    assert p3["input_urls"] == "https://a.example/1.jpg"
    p4 = zoo._payload(zoo.model("i2v:kie:omnihuman-1-5"), "", ["https://a.example/1.jpg"], resolution="1080",
                      extra={"audio_url": "https://a.example/voice.mp3"})
    assert p4["output_resolution"] == "1080"                         # per-model resolution field
    assert p4["image_url"] == "https://a.example/1.jpg" and p4["audio_url"].endswith(".mp3")
    assert "prompt" not in p4                                        # has_prompt False: portrait + audio only


def test_muapi_payload_unchanged():
    m = zoo.model("t2i:nano-banana")
    p = zoo._payload(m, "a red umbrella", [], aspect="16:9", num=2)
    assert p["aspect_ratio"] == "16:9" and p["num_images"] == 2      # num still mapped for muapi
    mv = zoo.model(next(x["id"] for x in zoo.load_catalog()["models"]
                        if x.get("gateway", "muapi") != "kie" and x["mode"] == "i2i"
                        and (x.get("max_images") or 0) >= 2))
    pm = zoo._payload(mv, "bg white", ["https://a.example/1.jpg", "https://a.example/2.jpg"])
    assert "images_list" in pm                                       # muapi multi-image param unchanged


# ------------------------------------------------------------------ fake kie gateway (no network)
class _Resp:
    def __init__(self, j, code=200):
        self._j, self.status_code, self._t = j, code, "ok"

    @property
    def text(self):
        return self._t

    @property
    def content(self):
        return self._t.encode()

    def json(self):
        return self._j


class _KieClient:
    """createTask -> taskId; recordInfo -> scripted states; CDN upload -> downloadUrl."""
    calls, script = [], []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        _KieClient.calls.append(("POST", url, json, dict(headers or {})))
        if "file-base64-upload" in url:
            return _Resp({"code": 200, "data": {"downloadUrl": "https://kie-cdn.example/ref-1.jpg"}})
        return _Resp({"code": 200, "msg": "success", "data": {"taskId": "kie-task-9"}})

    async def get(self, url, headers=None, params=None):
        _KieClient.calls.append(("GET", url, params, dict(headers or {})))
        n = len([c for c in _KieClient.calls if c[0] == "GET"])
        step = min(n, len(_KieClient.script)) - 1
        return _Resp(_KieClient.script[max(0, step)])


def _kie_env(monkeypatch):
    monkeypatch.setenv("ZOO_KIE_KEY", "kie-test-key")
    for v in ("KIE_API_KEY", "ZOO_MUAPI_KEY", "MUAPI_KEY"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(zoo, "POLL_S", 0.01)
    monkeypatch.setattr(zoo, "_public", lambda u: None)   # hermetic: skip DNS check
    monkeypatch.setattr(zoo.httpx, "AsyncClient", _KieClient)
    _KieClient.calls, _KieClient.script = [], []


def test_key_falls_back_to_the_app_dotenv(monkeypatch, tmp_path):
    """Prod reality: the owner's keys live in $CORE/.env; pydantic only carries declared fields,
    so zoo reads the file itself when os.environ does not have the key (cwd = $CORE there)."""
    for v in ("ZOO_KIE_KEY", "KIE_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("OTHER=x\nZOO_KIE_KEY=dotenv-key-1\n")
    assert zoo.kie_key() == "dotenv-key-1"
    (tmp_path / ".env").write_text('ZOO_KIE_KEY="quoted-key"\n')
    assert zoo.kie_key() == "quoted-key"
    (tmp_path / ".env").unlink()
    assert zoo.kie_key() == ""
    monkeypatch.setenv("ZOO_KIE_KEY", "env-wins")
    (tmp_path / ".env").write_text("ZOO_KIE_KEY=dotenv-loses\n")
    assert zoo.kie_key() == "env-wins"          # os.environ first, .env only as fallback


def test_kie_make_without_key_is_a_clear_error(monkeypatch):
    for v in ("ZOO_KIE_KEY", "KIE_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(ZooError) as e:
        asyncio.run(zoo.run(zoo.model("t2i:kie:nano-banana-2"), "a red umbrella"))
    assert "ZOO_KIE_KEY" in str(e.value)
    # the muapi model keeps ITS error line (the old test still pins that on the same tree)
    with pytest.raises(ZooError) as e2:
        asyncio.run(zoo.run(zoo.model("t2i:nano-banana"), "a red umbrella"))
    assert "ZOO_MUAPI_KEY" in str(e2.value)


def test_kie_run_against_fake_gateway(monkeypatch):
    _kie_env(monkeypatch)
    _KieClient.script = [
        {"code": 200, "data": {"state": "waiting", "resultJson": "{}"}},
        {"code": 200, "data": {"state": "success",
                               "resultJson": json.dumps({"resultUrls": ["https://example.com/kv.jpg"]})}},
    ]
    recorded = {}

    def fake_record(model, **kw):
        recorded["model"] = model
        return 0.0

    import app.usage as usage
    monkeypatch.setattr(usage, "record", fake_record)
    m = zoo.model("t2i:kie:nano-banana-2")
    r = asyncio.run(zoo.run(m, "a red umbrella on a beach", tenant="t1", wait_s=5))
    assert r["request_id"] == "kie:kie-task-9"                   # prefixed so status() routes to kie
    assert r["status"] == "done" and r["urls"] == ["https://example.com/kv.jpg"]
    post = next(c for c in _KieClient.calls if c[0] == "POST")
    assert post[1].endswith("/api/v1/jobs/createTask")
    assert post[3]["Authorization"] == "Bearer kie-test-key"     # key travels as Bearer - only to kie
    assert post[2]["model"] == "nano-banana-2"                   # the endpoint IS the kie model name
    assert post[2]["input"]["prompt"].startswith("a red umbrella")
    assert recorded["model"] == "zoo:kie:nano-banana-2"          # usage counted in the kie namespace
    get = next(c for c in _KieClient.calls if c[0] == "GET")
    assert get[1].endswith("/api/v1/jobs/recordInfo") and get[2] == {"taskId": "kie-task-9"}


def test_kie_aspect_default_injected_and_muapi_not(monkeypatch):
    """kie requires aspect_ratio (probe-proven): when she gives none, the entry's first is used.
    muapi keeps its exact old shape - no aspect invented there."""
    _kie_env(monkeypatch)
    _KieClient.script = [{"code": 200, "data": {"state": "success",
                                                "resultJson": json.dumps({"resultUrls": ["https://example.com/kv3.jpg"]})}}]
    r = asyncio.run(zoo.run(zoo.model("t2i:kie:nano-banana-2-lite"), "ek laal chhata beach par", wait_s=5))
    assert r["status"] == "done"
    post = next(c for c in _KieClient.calls if c[1].endswith("/api/v1/jobs/createTask"))
    assert post[2]["input"]["aspect_ratio"] == "1:1"            # first aspect of the entry
    p = zoo._payload(zoo.model("t2i:nano-banana"), "a red umbrella", [])
    assert "aspect_ratio" not in p                              # muapi untouched


def test_kie_poll_failed_carries_failmsg(monkeypatch):
    _kie_env(monkeypatch)
    _KieClient.script = [
        {"code": 200, "data": {"state": "fail", "failMsg": "content blocked by the model", "resultJson": "{}"}},
    ]
    r = asyncio.run(zoo.poll("kie:kie-task-9"))
    assert r["status"] == "failed" and "content blocked" in r["error"]


def test_kie_local_reference_uploads_to_cdn(monkeypatch):
    _kie_env(monkeypatch)
    _KieClient.script = [{"code": 200, "data": {"state": "success",
                                                "resultJson": json.dumps({"resultUrls": ["https://example.com/kv2.jpg"]})}}]
    m = zoo.model("i2i:kie:nano-banana-2")
    r = asyncio.run(zoo.run(m, "background white karo", tenant="t1",
                            image_urls=["data:image/png;base64,AAAA"], wait_s=5))
    up = next(c for c in _KieClient.calls if "file-base64-upload" in c[1])
    assert up[3]["Authorization"] == "Bearer kie-test-key" and up[2]["uploadPath"] == "hoola-zoo"
    post = next(c for c in _KieClient.calls if c[1].endswith("/api/v1/jobs/createTask"))
    assert post[2]["input"]["image_input"] == "https://kie-cdn.example/ref-1.jpg"   # CDN url, not the data URI
    assert r["status"] == "done"


# ------------------------------------------------------------------ the tool handler
def test_tool_models_rows_carry_gateway():
    out = asyncio.run(zoo_tool(CTX, "guide"))
    assert out["count"] == len(zoo.load_catalog()["models"]) >= 233 and "200+" in out["guide"]
    out = asyncio.run(zoo_tool(CTX, "models", q="kling", limit=100))
    assert out["count"] >= 4
    assert all("gateway" in m for m in out["models"])            # every row says which gateway
    kie_rows = [m for m in out["models"] if m["gateway"] == "kie"]
    assert kie_rows and all(m["id"].startswith(("t2v:kie:", "i2v:kie:", "v2v:kie:")) for m in kie_rows)


def test_tool_make_kie_end_to_end(monkeypatch):
    _kie_env(monkeypatch)
    _KieClient.script = [{"code": 200, "data": {"state": "success",
                                                "resultJson": json.dumps({"resultUrls": ["https://example.com/final.jpg"]})}}]
    r = asyncio.run(zoo_tool(CTX, "make", model_id="t2i:kie:nano-banana-2-lite", prompt="ek laal chhata beach par"))
    assert r["status"] == "done" and r["request_id"] == "kie:kie-task-9"
    assert "https://example.com/final.jpg" in r["say"]
    with pytest.raises(ToolError):
        asyncio.run(zoo_tool(CTX, "make", model_id="t2i:kie:nano-banana-2-lite",
                             prompt="nangi ladki banao"))        # the safety gate runs for kie too
