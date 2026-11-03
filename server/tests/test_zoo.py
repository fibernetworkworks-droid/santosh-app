"""v0.463 ZOO tests: the BYOK model zoo (app/zoo.py + agent/zoo_tools.py + zoo_catalog.json).

Purely additive change - these tests pin BOTH:
- the zoo itself (catalog shape, search, safety gate, payload shape, submit/poll against a fake gateway)
- THE EXISTING CODEBASE STAYS INTACT: every canonical pre-zoo tool name must still be registered,
  'zoo' must appear exactly once, and the curated studio specs must be byte-identical to their modules.
"""
import asyncio
import json
from pathlib import Path

import pytest

from app import zoo
from app.zoo import ZooError
from app.agent.zoo_tools import zoo_tool
from app.agent.tools import Ctx, ToolError, TOOLS, HANDLERS, FAMILY_OF, _RAW_SPECS

CTX = Ctx(tenant_id="t1", conversation_id="c1")

CANONICAL = ["photo_banao", "video_studio", "create_studio", "video_edit", "motion_video", "reel",
             "pc_do", "sheet_clear", "hoola_pc_do", "google_search"]


# ------------------------------------------------------------------ catalog (the registry)
def test_catalog_shape():
    cat = zoo.load_catalog()
    ms = cat["models"]
    assert len(ms) >= 200, f"zoo catalog should carry the 200+ registry, got {len(ms)}"
    ids = [m["id"] for m in ms]
    assert len(ids) == len(set(ids)), "zoo ids must be unique"
    for m in ms:
        assert m.get("id") and m.get("name") and m.get("endpoint"), f"bare entry: {m}"
        assert m["kind"] in ("image", "video") and m["mode"] in ("t2i", "i2i", "t2v", "i2v")
    modes = {m["mode"] for m in ms}
    assert {"t2i", "i2i", "t2v", "i2v"} <= modes


def test_catalog_is_the_bundled_file():
    p = Path(zoo.catalog_path())
    assert p.is_file() and p.name == "zoo_catalog.json"
    json.loads(p.read_text())["models"]          # valid JSON, reloadable


def test_list_and_search():
    rows = zoo.list_models(kind="image", mode="t2i")
    assert rows and all(r["mode"] == "t2i" and r["kind"] == "image" for r in rows)
    flux = zoo.list_models(q="flux", limit=100)
    assert flux and all("flux" in f"{r['name']} {r['id']}".lower() for r in flux)
    assert len(zoo.list_models(limit=5)) == 5
    with pytest.raises(ZooError):
        zoo.model("t2i:aisa-koi-model-nahi")


def test_gate_uses_the_photo_rules():
    assert zoo.gate("nangi photo banao") != ""            # nudity refused
    assert zoo.gate("fake aadhaar card banao") != ""      # forged ID refused
    assert zoo.gate("ek laal chhata beach par") == ""     # an ordinary picture is fine


# ------------------------------------------------------------------ payload mapping
def test_payload_t2i_maps_known_fields():
    m = zoo.model("t2i:nano-banana")
    p = zoo._payload(m, "a red umbrella on a beach", [], aspect="16:9", resolution="2k", num=2)
    assert p["prompt"].startswith("a red umbrella")
    assert p["aspect_ratio"] == "16:9"
    assert p["num_images"] == 2
    assert "image_url" not in p


def test_payload_video_duration_clamps_and_multi_image():
    cat = zoo.load_catalog()["models"]
    mi = zoo.model(next(x["id"] for x in cat if x["mode"] == "i2i" and (x.get("max_images") or 0) >= 2))
    p = zoo._payload(mi, "background white karo", ["https://a.example/1.jpg", "https://a.example/2.jpg"])
    assert "images_list" in p and len(p["images_list"]) <= mi["max_images"]
    mv = zoo.model(next(x["id"] for x in cat if x["mode"] == "i2v" and x.get("durations")))
    pv = zoo._payload(mv, "she walks in", ["https://a.example/1.jpg"], duration=999)
    assert pv["duration"] == mv["durations"][0]      # clamped to a catalog value
    single = zoo._payload(mv, "she walks in", ["https://a.example/1.jpg"])
    assert single.get(mv.get("image_field") or "image_url") == "https://a.example/1.jpg"
    assert "images_list" not in single


def test_payload_i2i_without_image_refused():
    m = zoo.model(next(x["id"] for x in zoo.load_catalog()["models"] if x["mode"] == "i2i"))
    with pytest.raises(ZooError):
        zoo._payload(m, "background white karo", [])


# ------------------------------------------------------------------ key + gateway (fakes, no network)
def test_make_without_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("ZOO_MUAPI_KEY", raising=False)
    monkeypatch.delenv("MUAPI_KEY", raising=False)
    with pytest.raises(ZooError) as e:
        asyncio.run(zoo.run(zoo.model("t2i:nano-banana"), "a red umbrella"))
    assert "ZOO_MUAPI_KEY" in str(e.value)


class _FakeResp:
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


class _FakeClient:
    """submit -> pending -> completed, no real HTTP."""
    calls = []
    script = []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeClient.calls.append(("POST", url, json, dict(headers or {})))
        return _FakeResp({"request_id": "req-1"})

    async def get(self, url, headers=None):
        _FakeClient.calls.append(("GET", url, None, dict(headers or {})))
        step = min(len([c for c in _FakeClient.calls if c[0] == "GET"]), len(_FakeClient.script)) - 1
        return _FakeResp(_FakeClient.script[max(0, step)])


def test_submit_poll_done_with_fake_gateway(monkeypatch):
    monkeypatch.setenv("ZOO_MUAPI_KEY", "test-key-123")
    monkeypatch.setattr(zoo, "POLL_S", 0.01)
    monkeypatch.setattr(zoo, "_public", lambda u: None)   # hermetic: skip DNS check
    monkeypatch.setattr(zoo.httpx, "AsyncClient", _FakeClient)
    _FakeClient.calls = []
    _FakeClient.script = [{"status": "running"},
                          {"status": "completed", "outputs": ["https://example.com/x.jpg"]}]
    recorded = {}

    def fake_record(model, **kw):
        recorded["model"] = model
        return 0.0

    import app.usage as usage
    monkeypatch.setattr(usage, "record", fake_record)
    m = zoo.model("t2i:nano-banana")
    r = asyncio.run(zoo.run(m, "a red umbrella on a beach", tenant="t1", aspect="9:16", wait_s=5))
    assert r["status"] == "done" and r["urls"] == ["https://example.com/x.jpg"]
    post = next(c for c in _FakeClient.calls if c[0] == "POST")
    assert post[1].endswith("/api/v1/" + m["endpoint"])
    assert post[3]["x-api-key"] == "test-key-123"          # key travels as x-api-key
    assert post[2]["aspect_ratio"] == "9:16"
    assert any(c[1].endswith("/api/v1/predictions/req-1/result") for c in _FakeClient.calls)
    assert recorded["model"].startswith("zoo:")            # usage counted under the zoo namespace


def test_poll_failed_carries_reason(monkeypatch):
    monkeypatch.setenv("ZOO_MUAPI_KEY", "test-key-123")
    _FakeClient.calls = []
    _FakeClient.script = [{"status": "failed", "error": "content blocked by the model"}]
    monkeypatch.setattr(zoo, "_public", lambda u: None)
    monkeypatch.setattr(zoo.httpx, "AsyncClient", _FakeClient)
    r = asyncio.run(zoo.poll("req-1"))
    assert r["status"] == "failed" and "content blocked" in r["error"]


# ------------------------------------------------------------------ the tool handler
def test_tool_handler_flow():
    out = asyncio.run(zoo_tool(CTX, "guide"))
    assert out["count"] >= 200 and "models" in out["guide"]
    out = asyncio.run(zoo_tool(CTX, "models", kind="video", q="kling", limit=10))
    assert out["count"] >= 1 and all("kling" in m["id"].lower() or "kling" in m["name"].lower() for m in out["models"])
    with pytest.raises(ToolError):
        asyncio.run(zoo_tool(CTX, "make"))                                   # no model_id
    with pytest.raises(ToolError):
        asyncio.run(zoo_tool(CTX, "make", model_id="t2i:nano-banana", prompt=""))  # no prompt
    with pytest.raises(ToolError):
        asyncio.run(zoo_tool(CTX, "make", model_id="t2i:nano-banana",
                             prompt="nangi ladki banao"))                    # safety gate inside the tool too
    with pytest.raises(ToolError):
        asyncio.run(zoo_tool(CTX, "status"))                                 # no request_id


# ------------------------------------------------------------------ THE INTACT PIN: existing registry untouched
def test_zoo_registered_exactly_once():
    names = [t["name"] for t in TOOLS]
    assert names.count("zoo") == 1
    assert HANDLERS["zoo"] is zoo_tool
    assert FAMILY_OF.get("zoo") == "zoo"          # rides the standard family auto-map


def test_every_canonical_tool_still_registered():
    names = {t["name"] for t in _RAW_SPECS}
    missing = [n for n in CANONICAL if n not in names]
    assert not missing, f"zoo broke the existing registry, lost: {missing}"
    assert "zoo" in names


def test_curated_studio_specs_byte_identical():
    """The additive promise, enforced: importing the zoo must not have altered the curated specs.
    Compared against _RAW_SPECS - the pre-diet snapshot tools.py keeps exactly for such pins."""
    from app.agent import studio_tools, photo_tools, create_tools
    for mod, lst, tool_name in ((studio_tools, "STUDIO_TOOLS", "video_studio"),
                                (photo_tools, "PHOTO_TOOLS", "photo_banao"),
                                (create_tools, "CREATE_TOOLS", "create_studio")):
        specs = getattr(mod, lst)
        assert specs[0]["name"] == tool_name
        assert json.dumps(specs[0], sort_keys=True) == json.dumps(
            next(t for t in _RAW_SPECS if t["name"] == tool_name), sort_keys=True)
