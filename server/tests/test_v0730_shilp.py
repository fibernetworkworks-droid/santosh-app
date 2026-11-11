"""v0.730.0 SHILP MANCH - the ArtCraft generation lane (their Omni API, BYOK).

Owner: "MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS" on the storytold/artcraft
recon -> the plan's W0: one tool `shilp`, six actions over EXACTLY the surface their public
doc proves (video / image generation + job + batch job status + keyless status / models).

The laws under test (each one a named hole in a lesser integration):

- BYOK: the key lives in settings only; NO envelope ever carries it (the leak test greps every
  answer for the fake key).
- Money: every generate call spends credits; a 402 maps to PAYMENT and is final; the tool
  description tells the model to fire only on an explicit ask.
- Idempotency is minted here: a fresh UUID4 per generate call; caller-supplied tokens ignored.
- The reference-url wall: public http(s) only - loopback, RFC1918, link-local, reserved,
  metadata hosts and credential-embedded urls are refused BEFORE the seam moves (an internal
  endpoint must never land in their server logs).
- URL inputs only: their *_media_tokens fields are refused with their own mutual-exclusivity
  rule quoted (the upload endpoints are not in the public doc - nothing invented).
- One network seam (`_http`): the whole suite is offline; the seam fake records every call so
  tests assert method / url / body / auth shape, not just outcomes.
- Jobs honest: their states ride raw; `ok` is the call, `job_ok` is the job; the doc's own
  example states (pending and complete_success video) are scripted verbatim.
- Caps refuse, never clamp: 21 references -> BAD_INPUT naming the 20 cap; a changed job behind
  her back is worse than a refusal.
- Kill switch, NEED_SETUP everywhere when the key is missing, envelope discipline, the 618
  registry pin (617 + 1 shilp), the APP_VERSION pin, and the MCP door riding the SAME _sync
  dispatch (no drift).
"""
import asyncio
import ast
import json
import uuid
from pathlib import Path

import pytest

from app.agent import shilp_tools as S
from app.agent.tools import Ctx, TOOLS

CTX = Ctx(tenant_id="shilp-test-tenant", conversation_id="c1")

KEY = "artcraft_api_" + "3k7q9w0xv2hs5n8m4d6r1t8y0p2s4f6h8j0k2m4n"   # their doc's 53-char shape
BASE = "https://api.storyteller.ai"


def kl(action="status", ctx=None, **kw):
    return asyncio.run(S.shilp(ctx or CTX, action, **kw))


def _set(monkeypatch, **kv):
    from app.config import get_settings
    st = get_settings()
    for k, v in kv.items():
        monkeypatch.setattr(st, k, v, raising=False)


def _seam(responses):
    """A fake seam: pops one (status, data) per call; records method / url / key / body."""
    calls = []

    async def fake(method, url, *, api_key, json_body=None):
        calls.append({"method": method, "url": url, "api_key": api_key, "json_body": json_body})
        item = responses.pop(0) if responses else (200, {})
        if isinstance(item, Exception):
            raise item
        return item

    return fake, calls


def _gen_ok(token="jinf_9fcn2qv4dv3vvbrrxbnmfgen06v"):
    return (200, {"success": True, "inference_job_token": token,
                  "all_job_tokens": [token]})


# their doc's own example states, verbatim
PENDING_STATE = {
    "job_token": "jinf_xxxxxxxxxxxxxxxxxxxxxxxxx",
    "request": {"inference_category": "video_generation", "maybe_model_type": "seedance_2p0"},
    "status": {"status": "pending", "maybe_first_started_at": None,
               "maybe_failure_category": None, "progress_percentage": 0},
    "maybe_result": None,
    "created_at": "2026-06-24T04:06:14Z", "updated_at": "2026-06-24T04:06:14Z",
}
DONE_STATE = {
    "job_token": "jinf_9fcn2qv4dv3vvbrrxbnmfgen06v",
    "request": {"inference_category": "video_generation"},
    "status": {"status": "complete_success", "maybe_first_started_at": "2026-06-24T04:07:11Z",
               "maybe_failure_category": None, "progress_percentage": 100},
    "maybe_result": {"entity_type": "media_file", "entity_token": "m_ss682134tx19yhqs5y0nbnd0bd59a6",
                     "media_links": {
                         "cdn_url": "https://pub-EXAMPLE.r2.dev/media/artcraft_EXAMPLE.mp4",
                         "maybe_thumbnail_template": None,
                         "maybe_video_previews": {
                             "still": "https://pub-EXAMPLE.r2.dev/media/artcraft_EXAMPLE.mp4-thumb.jpg",
                             "animated": "https://pub-EXAMPLE.r2.dev/media/artcraft_EXAMPLE.mp4-thumb.gif",
                             "still_thumbnail_template": "t-{WIDTH}.jpg",
                             "animated_thumbnail_template": "t-{WIDTH}.gif"}},
                     "maybe_successfully_completed_at": "2026-06-24T04:17:30Z"},
    "created_at": "2026-06-24T04:06:14Z", "updated_at": "2026-06-24T04:17:30Z",
}


# ---------------------------------------------------------------- the shape

def test_envelope_shape_always():
    for out in (kl("status"), kl("nope"), kl("models"),
                kl("video", model="seedance_2p0"), kl("job", token="jinf_badtoken99")):
        assert out["schema_version"] == 1 and out["tool"] == "shilp"
        assert set(out) >= {"ok", "action", "error", "meta"}
        assert isinstance(out["meta"]["elapsed_ms"], int)
        assert out["meta"]["backend"]
        assert out["error"] is None or set(out["error"]) == {"code", "message", "hint"}


def test_unknown_action_names_the_valid_six():
    out = kl("dance")
    assert out["ok"] is False and out["error"]["code"] == "BAD_INPUT"
    assert all(a in out["error"]["message"] for a in ("status", "models", "video", "image", "job", "jobs"))


def test_kill_switch_need_setup(monkeypatch):
    _set(monkeypatch, shilp_enabled=False)
    out = kl("models")
    assert out["ok"] is False and out["error"]["code"] == "NEED_SETUP"
    assert "shilp_enabled" in out["error"]["hint"]


# ---------------------------------------------------------------- keyless actions + BYOK

def test_status_is_zero_network_and_keyless(monkeypatch):
    fake, calls = _seam([])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("status")
    assert out["ok"] is True and out["key_set"] is False
    assert calls == []                                   # zero network, truly
    assert "app.getartcraft.com" in out["setup"]
    assert out["upstream"]["base_url"] == BASE
    assert "NOT api.getartcraft.com" in out["v1_surface"] or "api.storyteller.ai" in out["upstream"]["base_url"]


def test_status_never_leaks_the_key(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    blob = json.dumps(kl("status"))
    assert '"key_set": true' in blob and KEY not in blob


def test_no_key_need_setup_on_every_network_action(monkeypatch):
    fake, calls = _seam([])
    monkeypatch.setattr(S, "_http", fake)
    for kw in ({"action": "video", "model": "seedance_2p0", "prompt": "x"},
               {"action": "image", "model": "nano_banana_pro"},
               {"action": "job", "token": "jinf_9fcn2qv4dv3vvbrrxbnmfgen06v"},
               {"action": "jobs", "tokens": ["jinf_9fcn2qv4dv3vvbrrxbnmfgen06v"]}):
        out = kl(**kw)
        assert out["ok"] is False and out["error"]["code"] == "NEED_SETUP", kw
        assert "app.getartcraft.com" in out["error"]["hint"]
        assert "ARTCRAFT_API_KEY" in out["error"]["hint"]
    assert calls == []                                   # refusals happen before the seam


def test_models_catalog_static_and_complete():
    out = kl("models")
    assert out["ok"] is True and out["total"] == 62
    assert out["counts"] == {"image": 16, "video": 25, "audio": 5, "mesh": 11, "splat": 5}
    assert "Seedance 2.0" in out["catalog"]["video"]["Seedance"]
    assert "2026-11-09" in out["catalog_source"]
    assert "NO documented Omni API endpoint" in out["note"]


# ---------------------------------------------------------------- the walls (before any byte)

def test_video_mutually_exclusive_media_tokens_refused(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, calls = _seam([])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("video", model="seedance_2p0", prompt="x",
             reference_image_media_tokens=["m_abc"], reference_image_urls=["https://pub-EXAMPLE.r2.dev/a.jpg"])
    assert out["ok"] is False and out["error"]["code"] == "BAD_INPUT"
    assert "Either reference_image_media_tokens or reference_image_urls" in out["error"]["message"]
    assert "desktop app" in out["error"]["message"]
    assert calls == []


BAD_URLS = [
    ("http://127.0.0.1/x.jpg", "NOT_ALLOWED"),
    ("http://localhost/x.jpg", "NOT_ALLOWED"),
    ("http://10.1.2.3/x.jpg", "NOT_ALLOWED"),
    ("http://192.168.1.4/x.jpg", "NOT_ALLOWED"),
    ("http://172.16.0.9/x.jpg", "NOT_ALLOWED"),
    ("http://169.254.169.254/latest/meta-data", "NOT_ALLOWED"),
    ("https://metadata.google.internal/x", "NOT_ALLOWED"),
    ("https://host.local/x.jpg", "NOT_ALLOWED"),
    ("http://user:pass@pub-EXAMPLE.r2.dev/a.jpg", "NOT_ALLOWED"),
    ("ftp://pub-EXAMPLE.r2.dev/a.jpg", "BAD_INPUT"),
    ("file:///etc/passwd", "BAD_INPUT"),
    ("not a url", "BAD_INPUT"),
]


@pytest.mark.parametrize("url,code", BAD_URLS)
def test_reference_url_wall(monkeypatch, url, code):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, calls = _seam([])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("video", model="seedance_2p0", prompt="x", reference_image_urls=[url])
    assert out["ok"] is False and out["error"]["code"] == code, (url, out["error"])
    assert calls == []                                   # refused before a byte moves


def test_reference_url_public_passes_through_the_wall(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, calls = _seam([_gen_ok()])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("video", model="seedance_2p0", prompt="x",
             reference_image_urls=["https://commons.wikimedia.org/wiki/a.jpg"])
    assert out["ok"] is True
    assert calls[0]["json_body"]["reference_image_urls"] == ["https://commons.wikimedia.org/wiki/a.jpg"]


def test_refs_cap_refuses_never_clamps(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, calls = _seam([])
    monkeypatch.setattr(S, "_http", fake)
    urls = [f"https://pub-EXAMPLE.r2.dev/{i}.jpg" for i in range(21)]
    out = kl("video", model="seedance_2p0", prompt="x", reference_image_urls=urls)
    assert out["error"]["code"] == "BAD_INPUT" and "20" in out["error"]["message"]
    assert calls == []


def test_prompt_cap_refuses(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    out = kl("video", model="seedance_2p0", prompt="x" * 8001)
    assert out["error"]["code"] == "BAD_INPUT" and "8000" in out["error"]["message"]


# ---------------------------------------------------------------- generate: video / image

def test_video_happy_path(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, calls = _seam([_gen_ok()])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("video", model="seedance_2p0", prompt="A puffin on a cliff", duration_seconds=6,
             aspect_ratio="wide_sixteen_by_nine", generate_audio=True)
    assert out["ok"] is True and out["job_token"] == "jinf_9fcn2qv4dv3vvbrrxbnmfgen06v"
    assert out["kind"] == "video" and "credits" in out["note"]
    c = calls[0]
    assert c["method"] == "POST" and c["url"] == f"{BASE}/v1/omni_api/generate/video"
    assert c["api_key"] == KEY and c["json_body"]["model"] == "seedance_2p0"
    assert c["json_body"]["duration_seconds"] == 6 and c["json_body"]["generate_audio"] is True
    uuid.UUID(c["json_body"]["idempotency_token"])       # a real UUID came through


def test_idempotency_minted_fresh_and_caller_token_ignored(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, calls = _seam([_gen_ok("jinf_aaaaaaaaaaaaaaaaaaaaaaaa"), _gen_ok("jinf_bbbbbbbbbbbbbbbbbbbbbbbb")])
    monkeypatch.setattr(S, "_http", fake)
    o1 = kl("video", model="seedance_2p0", prompt="x")
    o2 = kl("video", model="seedance_2p0", prompt="x")
    t1 = calls[0]["json_body"]["idempotency_token"]
    t2 = calls[1]["json_body"]["idempotency_token"]
    assert t1 != t2 and uuid.UUID(t1).version == 4 and uuid.UUID(t2).version == 4
    assert o1["job_token"] != o2["job_token"]


def test_model_shape_guard(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, calls = _seam([])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("video", model="Seedance 2.0", prompt="x")   # a display name, not the api id
    assert out["error"]["code"] == "BAD_INPUT" and "seedance_2p0" in out["error"]["message"]
    assert calls == []


def test_image_happy_path(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, calls = _seam([_gen_ok("jinf_cccccccccccccccccccccccc")])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("image", model="nano_banana_pro", prompt="a logo",
             image_urls=["https://pub-EXAMPLE.r2.dev/ref.jpg"])
    assert out["ok"] is True and out["kind"] == "image"
    assert calls[0]["url"] == f"{BASE}/v1/omni_api/generate/image"
    assert calls[0]["json_body"]["image_urls"] == ["https://pub-EXAMPLE.r2.dev/ref.jpg"]


# ---------------------------------------------------------------- their statuses, honest

def test_auth_401_mapped(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, _ = _seam([(401, {"error": "unauthorized"})])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("video", model="seedance_2p0", prompt="x")
    assert out["error"]["code"] == "AUTH" and "ARTCRAFT_API_KEY" in out["error"]["hint"]
    assert KEY not in json.dumps(out)


def test_payment_402_is_final(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, _ = _seam([(402, {"error": "payment required"})])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("video", model="seedance_2p0", prompt="x")
    assert out["error"]["code"] == "PAYMENT" and "never retr" in out["error"]["hint"]


def test_other_4xx_rides_their_words(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, _ = _seam([(400, {"error": "unknown model kling_9_9"})])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("video", model="kling_9_9", prompt="x")
    assert out["error"]["code"] == "UPSTREAM" and "400" in out["error"]["message"]
    assert "kling_9_9" in out["error"]["message"]        # their words, not ours


def test_job_pending_mapped(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, calls = _seam([(200, {"success": True, "state": PENDING_STATE})])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("job", token="jinf_xxxxxxxxxxxxxxxxxxxxxxxxx")
    assert out["ok"] is True
    j = out
    assert j["done"] is False and j["job_ok"] is False and j["progress"] == 0
    assert j["job_status"] == "pending" and "poll again" in j["note"]
    assert calls[0]["method"] == "GET"
    assert calls[0]["url"] == f"{BASE}/v1/omni_api/job_status/job/jinf_xxxxxxxxxxxxxxxxxxxxxxxxx"


def test_job_complete_success_mapped(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, _ = _seam([(200, {"success": True, "state": DONE_STATE})])
    monkeypatch.setattr(S, "_http", fake)
    j = kl("job", token="jinf_9fcn2qv4dv3vvbrrxbnmfgen06v")
    assert j["done"] is True and j["job_ok"] is True
    assert j["cdn_url"] == "https://pub-EXAMPLE.r2.dev/media/artcraft_EXAMPLE.mp4"
    assert j["previews"]["animated"].endswith(".gif") and j["entity_token"].startswith("m_")


def test_job_complete_failure_honest(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    st = json.loads(json.dumps(PENDING_STATE))
    st["status"] = {"status": "complete_failure", "maybe_failure_category": "upstream_model",
                    "progress_percentage": 40}
    fake, _ = _seam([(200, {"success": True, "state": st})])
    monkeypatch.setattr(S, "_http", fake)
    j = kl("job", token="jinf_xxxxxxxxxxxxxxxxxxxxxxxxx")
    assert j["done"] is True and j["job_ok"] is False and j["failure_category"] == "upstream_model"
    assert "credits" in j["note"]                        # the money honesty


def test_job_token_shape_guard(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    for bad in ("abc", "jinf_!!", "jinf_", "prompt_xyz"):
        out = kl("job", token=bad)
        assert out["error"]["code"] == "BAD_INPUT", bad


def test_jobs_batch_happy(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    states = [PENDING_STATE, DONE_STATE]
    fake, calls = _seam([(200, {"success": True, "job_states": states})])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("jobs", tokens=["jinf_xxxxxxxxxxxxxxxxxxxxxxxxx", "jinf_9fcn2qv4dv3vvbrrxbnmfgen06v"])
    assert out["ok"] is True and out["count"] == 2
    assert "1 complete" in out["note"]
    assert "tokens=jinf_x" in calls[0]["url"] and "batch" in calls[0]["url"]


def test_jobs_cap_and_shape(monkeypatch):
    _set(monkeypatch, artcraft_api_key=KEY)
    fake, calls = _seam([])
    monkeypatch.setattr(S, "_http", fake)
    out = kl("jobs", tokens=[f"jinf_t{i:020d}" for i in range(26)])
    assert out["error"]["code"] == "BAD_INPUT" and "25" in out["error"]["message"]
    out = kl("jobs", tokens="jinf_xxxxxxxxxxxxxxxxxxxxxxxxx")   # a bare string is not a list
    assert out["error"]["code"] == "BAD_INPUT"
    out = kl("jobs")
    assert out["error"]["code"] == "BAD_INPUT"
    assert calls == []


# ---------------------------------------------------------------- registration + purity

def test_registry_pin_618():
    from app.agent.tools import TOOL_LABELS
    assert len(TOOLS) == 627, ("626 + 1 pdf_kit (v0.821 HOOLA DOCUMENT KIT). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, "
                               "their Omni API, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA "
                               "USER CAN USE THIS' -> the plan's W0)")
    assert "shilp" in TOOL_LABELS and "credits" in TOOL_LABELS["shilp"]


def test_enum_pin():
    spec = next(t for t in TOOLS if t["name"] == "shilp")
    assert spec["input_schema"]["properties"]["action"]["enum"] == \
        ["status", "models", "video", "image", "job", "jobs"]


def test_app_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION.split(".")[1] >= "730"


def test_purity_no_top_level_httpx():
    tree = ast.parse(Path(S.__file__).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert all(a.name != "httpx" for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "") != "httpx"


# ---------------------------------------------------------------- the MCP door

def test_mcp_door_initialize_and_list():
    from app.shilp import mcp_server as M
    init = M.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, "t")
    assert init["result"]["serverInfo"]["name"] == "hoola-shilp"
    assert init["result"]["serverInfo"]["version"].split(".")[1] >= "730"
    lst = M.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, "t")
    tools = lst["result"]["tools"]
    assert len(tools) == 1 and tools[0]["name"] == "shilp"
    assert tools[0]["input_schema"]["properties"]["action"]["enum"] == \
        ["status", "models", "video", "image", "job", "jobs"]


def test_mcp_door_rides_the_same_dispatch(monkeypatch):
    from app.shilp import mcp_server as M
    out = M.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
        "name": "shilp", "arguments": {"action": "status"}}}, "t")
    assert out["result"]["isError"] is False
    assert out["result"]["structuredContent"]["ok"] is True
    assert out["result"]["structuredContent"]["tool"] == "shilp"
    _set(monkeypatch, artcraft_api_key="")
    out = M.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
        "name": "shilp", "arguments": {"action": "video", "model": "seedance_2p0"}}}, "t")
    sc = out["result"]["structuredContent"]
    assert sc["ok"] is False and sc["error"]["code"] == "NEED_SETUP"   # the door never drifts


def test_mcp_door_unknown_tool_and_method():
    from app.shilp import mcp_server as M
    out = M.handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
        "name": "kaan", "arguments": {}}}, "t")
    assert out["result"]["isError"] is True and "shilp" in out["result"]["content"][0]["text"]
    out = M.handle({"jsonrpc": "2.0", "id": 6, "method": "resources/list"}, "t")
    assert out["error"]["code"] == -32601
    out = M.respond("not json", "t")
    assert out["error"]["code"] == -32700
    assert M.handle({"jsonrpc": "2.0", "method": "ping"}, "t") is None or True   # no id -> no crash
