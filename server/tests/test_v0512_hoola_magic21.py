"""v0.512.0 HOOLA 21ST - the 21st-dev/magic-mcp port (owner: 'now this read first properly
and then feed to hoola ai'). The repo was read end-to-end first (21st-dev/magic-mcp @
6b5299e8 - Magic MCP is DEAD as a standalone, it is the unified 21st MCP: the package is a
thin stdio->HTTP proxy, the real product is https://21st.dev/api/mcp with x-api-key, and the
proxy IS the protocol documentation); this suite pins the port against upstream's own
file:line facts:

(1) TOOL SHAPE: ONE magic21 tool, five ops (list/usage/search/get/call) - the
    skill_manage/delegate_task/docs7 law. The op set mirrors the upstream surface
    (README tool table + skills/21st-ui/SKILL.md) with the legacy-name translation table
    carried (21st_magic_component_builder->generate, logo_search->search_logo).
(2) THE WIRE: initialize -> notifications/initialized -> tools/call|tools/list per op
    (stateless between turns - the pinned deviation); the Mcp-Session-Id echo rides the
    later POSTs (index.ts:159-165); the notification carries no id and expects no reply
    (index.ts:154-157); x-api-key + user-agent hoola-coder/0.511.0 + the
    "application/json, text/event-stream" accept header (index.ts:138-146).
(3) AUTH, THE UPSTREAM LESSONS: no key answers LOCALLY with zero network (index.ts:167-172);
    the endpoint's NOT_AUTHED sentence rides VERBATIM (index.ts:107-109); a 401 LATCHES the
    process - every later call answers offline (index.ts:146-152, the ~100k doomed
    initialize retries/hour lesson).
(4) THE STOP-LAW: a result carrying ai_subscription_required returns ok:False with the
    README's own instruction - stop generation attempts (aliases and CLI included), refresh
    tools after enabling AI; aiGenerationEnabled reports ACCESS, not balance.
(5) REDACTION BEFORE EGRESS: every string leaf of the outbound arguments passes
    strip_private + redact_secrets before the seam (upstream WARNS; Hoola enforces).
(6) VOICE-BOX CAPS: ONE attempt drop-don't-wait (a raised _http = clean fail-closed dict);
    a per-tenant rolling-hour window over OPS.
(7) KILL SWITCHES: coder_magic21 default OFF, coder_enabled master - both fail-closed with
    NO network call.
(8) THE SEED LANE: skillpack/mg-21st-ui.md under its own once-ever stamp
    (skills:magicpack:<tenant>, the v0.492 pattern), found by _pack_seeders by name,
    create-if-missing, hers win, the 4,000-char cap, the search-first + entitlement +
    stop-law content pins; seed_files excludes the mg- prefix (starter stays 11).
(9) THE ARCHIVE: upstream/21st-magic-mcp/ rides verbatim (ISC, LICENSE + PROVENANCE).
(10) WIRING: package export (the v0.478 lesson), agent/tools.py mount, voice absence,
     config defaults, APP_VERSION + pubspec pins.
Every network test rides the ONE seam (magic21._http) - no test touches the real network.
"""
import asyncio
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

T, CONV = "tenant-magic21", "conv-magic21"

NOT_AUTHED_UPSTREAM = (
    "Not authenticated - your API key is missing or was reset. Get a fresh key at "
    "https://21st.dev/mcp and update your MCP config (x-api-key / Bearer).")


def _ctx(tenant=T):
    return type("C", (), {"tenant_id": tenant, "conversation_id": CONV})()


def _call(*args, **kw):
    """The house async-call pattern (asyncio.run, the docs7/swarm suites' shape)."""
    from app.coder import magic21
    return asyncio.run(magic21.magic21(*args, **kw))


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """magic21 ON with a fresh key, window generous unless a test shrinks it, the 401
    latch and the window reset around every test (both are process-global)."""
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_MAGIC21", "true")
    monkeypatch.setenv("MAGIC21_API_KEY", "test-key-21st")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app.coder import magic21
    magic21._reset_auth_latch()
    magic21._window_reset()
    yield monkeypatch
    magic21._reset_auth_latch()
    magic21._window_reset()
    get_settings.cache_clear()


class _Spy:
    """The ONE network seam, faked: records every POST, replays scripted (status, headers,
    body) responses; the last script entry repeats when the script runs dry."""

    def __init__(self, script):
        self.script = list(script)
        self.calls: list[dict] = []

    async def __call__(self, url, headers, body, timeout):
        self.calls.append({"url": url, "headers": dict(headers),
                           "msg": json.loads(body) if body.strip() else None,
                           "raw_body": body, "timeout": timeout})
        i = min(len(self.calls) - 1, len(self.script) - 1)
        st, hd, text = self.script[i]
        return st, dict(hd), text


def _bomb():
    async def _no_network(*a, **k):
        raise AssertionError("network called - this path must be offline")
    return _no_network


_INIT_RESULT = {"jsonrpc": "2.0", "id": 1, "result": {
    "protocolVersion": "2025-03-26", "capabilities": {},
    "serverInfo": {"name": "21st", "version": "1.0.1"}}}


def _script_with_result(text, is_error=False):
    """init 200 (+session) -> notification 200 empty -> tools/call 200 with a text result."""
    result = {"jsonrpc": "2.0", "id": 2,
              "result": {"content": [{"type": "text", "text": text}], "isError": is_error}}
    return [(200, {"mcp-session-id": "sess-21st-1"}, json.dumps(_INIT_RESULT)),
            (200, {}, ""),
            (200, {}, json.dumps(result))]


# ------------------------------------------------------------------ (1) shape + wiring

def test_one_tool_five_ops_shape(env):
    from app.coder import magic21
    assert len(magic21.MAGIC21_TOOLS) == 1
    t = magic21.MAGIC21_TOOLS[0]
    assert t["name"] == "magic21"
    ops = t["input_schema"]["properties"]["op"]["enum"]
    assert ops == ["list", "usage", "search", "get", "call"]
    assert t["input_schema"]["required"] == ["op"]
    # the README tool table, carried in the schema: legacy names, current names
    assert magic21.LEGACY_NAMES["21st_magic_component_builder"] == "generate"
    assert magic21.LEGACY_NAMES["21st_magic_component_inspiration"] == "get_inspiration"
    assert magic21.LEGACY_NAMES["21st_magic_component_refiner"] == "generate"
    assert magic21.LEGACY_NAMES["logo_search"] == "search_logo"
    for n in ("search", "get_component", "generate", "get_inspiration", "search_logo"):
        assert n in magic21.CURRENT_TOOLS


def test_registry_mount(env):
    from app.agent import tools
    assert "magic21" in tools.HANDLERS and "magic21" in tools.TOOL_LABELS
    assert any(t["name"] == "magic21" for t in tools.TOOLS)
    assert len(tools.TOOLS) == 627, "626 + 1 pdf_kit (v0.819 HOOLA DOCUMENT KIT). 625 + 1 hoola_design (v0.817.0 HOOLA DESIGN: the design editor's one tool). 623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " "581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 541 (v0.502) + 1 magic21 (v0.512) + 1 dhara_dsl (their v0.514) + 10 construction (v0.522) + 1 crew_run (v0.523) + 2 from main's v0.533 CRAWL BRAIN wiring (healed in v0.537: this pin was red on pristine main) + 1 reach (v0.559 REACH MANCH) + 1 speckit (v0.569 SPEC SUTRA)"


def test_voice_absence(env):
    """A marketplace round-trip has no place in a live call - voice never sees magic21 (the
    docs7/delegate_task precedent)."""
    from app import voice
    assert "magic21" not in voice.VOICE_TOOL_NAMES


def test_package_export(env):
    """The v0.478 funnel lesson: coder.magic21 must exist on the PACKAGE path."""
    from app import coder
    assert hasattr(coder, "magic21") and "magic21" in coder.__all__
    assert coder.magic21.MAGIC21_HANDLERS["magic21"] is not None
    assert callable(coder.magic21._list_tools)


def test_config_defaults(env, monkeypatch):
    """The DEFAULTS, read with the fixture's opt-ins removed (the deployment opts in, not config.py)."""
    monkeypatch.delenv("CODER_MAGIC21", raising=False)
    monkeypatch.delenv("MAGIC21_API_KEY", raising=False)
    monkeypatch.delenv("MAGICPACK_ENABLED", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    st = get_settings()
    assert st.coder_magic21 is False            # the kill switch, default OFF
    assert st.magic21_api_url == "https://21st.dev/api/mcp"
    assert st.magic21_api_key == ""             # BYOK; never in chat
    assert st.coder_magic21_timeout_s == 20
    assert st.coder_magic21_max_per_hour == 12
    assert st.magicpack_enabled is True
    get_settings.cache_clear()


def test_version(env):
    from app import main as main_mod
    from pathlib import Path as P
    assert main_mod.APP_VERSION == "0.819.0"
    story = P(main_mod.__file__).read_text().split("APP_VERSION = ", 1)[1][:20000]
    # the newest-story precedent (established in the v0.520 rebase): the story pin
    # rides the NEWEST story - now the v0.530 HOOLA GRAPH story
    # story pin moved to the newest story (the newest-story precedent)
    assert "HOOLA RETRIEVE" in story and "index()" in story and "retriever" in story  # the newest-story precedent (the P5 markers live in the Previous chain)
    pub = (REPO_ROOT / "pubspec.yaml").read_text(encoding="utf-8")
    assert "version: 0.819.0+818" in pub


# ------------------------------------------------------------------ (7) kill switches

def test_kill_switch_off_fail_closed(env, monkeypatch):
    """coder_magic21 default OFF - the handler refuses with ZERO network (the docs7 shape)."""
    from app.coder import magic21
    monkeypatch.setenv("CODER_MAGIC21", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(magic21, "_http", _bomb())
    out = _call(_ctx(), op="search", query="pricing table")
    assert out["ok"] is False and "coder_magic21" in out["error"]
    get_settings.cache_clear()


def test_coder_master_fail_closed(env, monkeypatch):
    from app.coder import magic21
    monkeypatch.setenv("CODER_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(magic21, "_http", _bomb())
    out = _call(_ctx(), op="list")
    assert out["ok"] is False and "coder_enabled" in out["error"]
    get_settings.cache_clear()


# ------------------------------------------------------------------ (3) auth laws

def test_no_key_answers_locally_with_zero_network(env, monkeypatch):
    """index.ts:167-172: the proxy answers locally when no key was found; the endpoint
    requires auth for discovery AND calls (server.json isRequired) - no POST is spent."""
    from app.coder import magic21
    monkeypatch.setenv("MAGIC21_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(magic21, "_http", _bomb())
    out = _call(_ctx(), op="search", query="pricing table")
    assert out["ok"] is False and out["error"] == magic21.NOT_AUTHED
    assert out["code"] == -32001
    get_settings.cache_clear()


def test_not_authed_sentence_is_upstream_verbatim(env):
    """index.ts:107-109, byte for byte - the agent reads the same sentence however the
    refusal arrived."""
    from app.coder import magic21
    assert magic21.NOT_AUTHED == NOT_AUTHED_UPSTREAM
    src = (REPO_ROOT / "server/app/coder/skillpack/upstream/21st-magic-mcp/src/index.ts"
           ).read_text(encoding="utf-8")
    assert magic21.NOT_AUTHED in src


def test_401_latches_the_process(env, monkeypatch):
    """index.ts:146-152: one 401 and every later call answers offline - upstream saw ~100k
    doomed initialize retries an hour; the latch is the lesson."""
    from app.coder import magic21
    spy = _Spy([(401, {}, json.dumps({"jsonrpc": "2.0", "id": None,
                                      "error": {"code": -32001, "message": NOT_AUTHED_UPSTREAM}}))])
    monkeypatch.setattr(magic21, "_http", spy)
    out1 = _call(_ctx(), op="search", query="navbar")
    assert out1["ok"] is False and out1["error"] == NOT_AUTHED_UPSTREAM
    assert len(spy.calls) == 1                       # the initialize POST, then refused
    bomb = _bomb()
    monkeypatch.setattr(magic21, "_http", bomb)
    out2 = _call(_ctx(), op="search", query="hero")   # latched: zero network
    assert out2["ok"] is False and out2["error"] == NOT_AUTHED_UPSTREAM


# ------------------------------------------------------------------ (2) the wire

def test_wire_sequence_and_session_echo(env, monkeypatch):
    """initialize -> notifications/initialized -> tools/call: three POSTs, the session id
    echo riding the later POSTs (index.ts:159-165), the notification carrying no id
    (index.ts:154-157), the house user-agent + the MCP accept header (index.ts:138-146)."""
    from app.coder import magic21
    spy = _Spy(_script_with_result("found: pricing-table-pro, pricing-table-lite"))
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="search", query="pricing table")
    assert out["ok"] is True and "pricing-table-pro" in out["text"] and out["tool"] == "search"
    assert len(spy.calls) == 3
    c0, c1, c2 = spy.calls
    assert c0["msg"]["method"] == "initialize"
    assert c0["msg"]["params"]["protocolVersion"] == magic21.PROTOCOL_VERSION
    assert c0["msg"]["params"]["clientInfo"]["name"] == "hoola-coder"
    assert c0["headers"]["x-api-key"] == "test-key-21st"
    assert "mcp-session-id" not in c0["headers"]
    assert c1["msg"]["method"] == "notifications/initialized"
    assert "id" not in c1["msg"]
    assert c1["headers"]["mcp-session-id"] == "sess-21st-1"
    assert c2["msg"]["method"] == "tools/call"
    assert c2["msg"]["params"]["name"] == "search"
    assert c2["msg"]["params"]["arguments"] == {"query": "pricing table"}
    assert c2["headers"]["mcp-session-id"] == "sess-21st-1"
    assert c2["headers"]["user-agent"].startswith("hoola-coder/")
    assert "text/event-stream" in c2["headers"]["accept"]
    assert c2["msg"]["id"] == 2


def test_tools_list_entitlement_aware(env, monkeypatch):
    """op=list = tools/list; the reply names the account's tools; generate_listed reports
    whether hosted AI generation is on THIS account (README 'AI access')."""
    from app.coder import magic21
    listing = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [
        {"name": "search", "description": "Search the catalog"},
        {"name": "get_component", "description": "Fetch full code"},
        {"name": "get_usage", "description": "Account usage"},
    ]}}
    spy = _Spy([(200, {"mcp-session-id": "s9"}, json.dumps(_INIT_RESULT)),
                (200, {}, ""),
                (200, {}, json.dumps(listing))])
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="list")
    assert out["ok"] is True
    assert out["tools"] == ["search", "get_component", "get_usage"]
    assert out["generate_listed"] is False           # the entitlement door, honestly reported
    assert spy.calls[2]["msg"]["method"] == "tools/list"


def test_generate_listed_true_when_ai_on(env, monkeypatch):
    from app.coder import magic21
    listing = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [
        {"name": "search", "description": "Search"},
        {"name": "generate", "description": "Hosted AI UI generation"},
    ]}}
    spy = _Spy([(200, {"mcp-session-id": "s9"}, json.dumps(_INIT_RESULT)),
                (200, {}, ""), (200, {}, json.dumps(listing))])
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="list")
    assert out["ok"] is True and out["generate_listed"] is True


def test_op_call_passthrough_with_legacy_translation(env, monkeypatch):
    """op=call rides any tool by its CURRENT name; the legacy names translate BEFORE the
    wire (the README table, so old muscle memory keeps working)."""
    from app.coder import magic21
    spy = _Spy(_script_with_result("<svg>logo</svg>"))
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="call", name="logo_search", arguments={"query": "Zomato"})
    assert out["ok"] is True and "<svg>" in out["text"]
    assert spy.calls[2]["msg"]["params"]["name"] == "search_logo"   # translated
    assert spy.calls[2]["msg"]["params"]["arguments"] == {"query": "Zomato"}


def test_op_get_targets_get_component(env, monkeypatch):
    from app.coder import magic21
    spy = _Spy(_script_with_result("import { Button } from './ui/button'"))
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="get", arguments={"id": "pricing-table-pro"})
    assert out["ok"] is True and "Button" in out["text"]
    assert spy.calls[2]["msg"]["params"]["name"] == "get_component"


def test_op_usage_calls_get_usage(env, monkeypatch):
    """The SKILL.md gate, one op away: check get_usage BEFORE any generate."""
    from app.coder import magic21
    spy = _Spy(_script_with_result('{"aiGenerationEnabled": false}'))
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="usage")
    assert out["ok"] is True and "aiGenerationEnabled" in out["text"]
    assert spy.calls[2]["msg"]["params"]["name"] == "get_usage"


# ------------------------------------------------------------------ (5) redaction

def test_redaction_before_egress(env, monkeypatch):
    """Upstream WARNS in the skill; Hoola enforces: the secret NEVER crosses the seam."""
    from app.coder import magic21
    spy = _Spy(_script_with_result("ok"))
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="call", name="search",
                arguments={"query": "deploy note password=hunter2secret please",
                           "nested": {"token": "sk-a1b2c3d4e5f6g7h8i9j0k1"}, "keep": 7})
    assert out["ok"] is True
    sent = json.dumps(spy.calls[2]["msg"]["params"]["arguments"])
    assert "hunter2secret" not in sent and "***redacted***" in sent
    assert "sk-a1b2c3d4e5f6g7h8i9j0k1" not in sent
    assert sent.count("***redacted***") >= 2         # the leaf AND the nested leaf


def test_search_query_redacted_too(env, monkeypatch):
    from app.coder import magic21
    spy = _Spy(_script_with_result("ok"))
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="search", query="pricing table for <private>my api key 12345</private> dashboards")
    assert out["ok"] is True
    sent = spy.calls[2]["msg"]["params"]["arguments"]["query"]
    assert "my api key 12345" not in sent and "pricing table" in sent


# ------------------------------------------------------------------ (4) the stop-law

def test_ai_subscription_required_stops(env, monkeypatch):
    """README 'AI access' + SKILL.md workflow 2: the marker means STOP - no retries through
    legacy aliases or the CLI; refresh tools after enabling AI."""
    from app.coder import magic21
    spy = _Spy(_script_with_result("error: ai_subscription_required - upgrade to generate"))
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="call", name="21st_magic_component_builder",  # even through an alias
                arguments={"prompt": "a hero section"})
    assert out["ok"] is False
    assert "ai_subscription_required" in out["error"]
    assert "Stop generation attempts" in out["error"] and "refresh the tool list" in out["error"]
    assert "credit balance" in out["error"]


# ------------------------------------------------------------------ reply shapes

def test_sse_data_fallback_parsed(env, monkeypatch):
    """accept: application/json, text/event-stream (index.ts:139) - the SSE data: shape is a
    legal reply and parses."""
    from app.coder import magic21
    sse = ('data: {"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text",'
           '"text":"via sse"}]}}\n\n')
    spy = _Spy([(200, {"mcp-session-id": "s1"}, json.dumps(_INIT_RESULT)),
                (200, {}, ""), (200, {}, sse)])
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="search", query="dashboard")
    assert out["ok"] is True and out["text"] == "via sse"


def test_empty_body_is_an_honest_error(env, monkeypatch):
    """index.ts:178-182: an empty body is an error, never a silent success."""
    from app.coder import magic21
    spy = _Spy([(200, {"mcp-session-id": "s1"}, json.dumps(_INIT_RESULT)),
                (200, {}, ""), (200, {}, "")])
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="search", query="form")
    assert out["ok"] is False and "Empty response" in out["error"]


def test_unreachable_fail_closed(env, monkeypatch):
    """One attempt, drop-don't-wait: a raised seam is a clean dict, never an exception out
    of the handler."""
    from app.coder import magic21

    async def _raise(url, headers, body, timeout):
        raise TimeoutError("connect timeout")
    monkeypatch.setattr(magic21, "_http", _raise)
    out = _call(_ctx(), op="search", query="hero")
    assert out["ok"] is False and "21st MCP unreachable" in out["error"]
    assert "TimeoutError" in out["error"]


def test_mcp_error_reply_is_honest(env, monkeypatch):
    from app.coder import magic21
    err = {"jsonrpc": "2.0", "id": 2, "error": {"code": -32602, "message": "Unknown tool: nope"}}
    spy = _Spy([(200, {"mcp-session-id": "s1"}, json.dumps(_INIT_RESULT)),
                (200, {}, ""), (200, {}, json.dumps(err))])
    monkeypatch.setattr(magic21, "_http", spy)
    out = _call(_ctx(), op="call", name="nope")
    assert out["ok"] is False and "Unknown tool" in out["error"]


# ------------------------------------------------------------------ (6) caps

def test_courtesy_window_counts_ops(env, monkeypatch):
    """The rolling-hour window counts OPS (each op costs three wire POSTs - the bridge's own
    business, not her quota)."""
    from app.coder import magic21
    monkeypatch.setenv("CODER_MAGIC21_MAX_PER_HOUR", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    spy = _Spy(_script_with_result("ok"))
    monkeypatch.setattr(magic21, "_http", spy)
    assert _call(_ctx(), op="search", query="navbar")["ok"] is True
    assert _call(_ctx(), op="search", query="hero")["ok"] is True
    posts_after_two = len(spy.calls)                 # 2 ops = 6 POSTs
    out3 = _call(_ctx(), op="search", query="table")
    assert out3["ok"] is False and "courtesy window" in out3["error"]
    assert len(spy.calls) == posts_after_two         # the third op spent ZERO network
    get_settings.cache_clear()


def test_empty_search_query_refused_without_network(env, monkeypatch):
    from app.coder import magic21
    monkeypatch.setattr(magic21, "_http", _bomb())
    out = _call(_ctx(), op="search", query="   ")
    assert out["ok"] is False and "query is required" in out["error"]


def test_get_without_arguments_refused(env, monkeypatch):
    from app.coder import magic21
    monkeypatch.setattr(magic21, "_http", _bomb())
    out = _call(_ctx(), op="get")
    assert out["ok"] is False and "arguments" in out["error"]


def test_unknown_op(env, monkeypatch):
    from app.coder import magic21
    monkeypatch.setattr(magic21, "_http", _bomb())
    out = _call(_ctx(), op="inspire")
    assert out["ok"] is False and "unknown op" in out["error"]
    for word in ("list", "usage", "search", "get", "call"):
        assert word in out["error"]


# ------------------------------------------------------------------ (8) the seed lane

def test_mg_lane_counts(env):
    from app.coder import skill_packs
    mg = skill_packs.mg_files()
    assert len(mg) == 1
    assert {f.stem for f in mg} == {"mg-21st-ui"}
    assert len(skill_packs.seed_files()) == 11       # the starter lane untouched (mg- excluded)
    assert len(skill_packs.byox_files()) == 31 and len(skill_packs.prog_files()) == 2
    seed_dir = skill_packs.SEED_DIR
    assert len(list(seed_dir.glob("*.md"))) == 99    # 11 + 31 + 2 + 15 + 3 + 2 + 1 + 2 + 1 + 2 + 2 + 27, TWENTY-NINE lanes (th- v0.547, ed- v0.548, the 18 omni families v0.561)
    seeder_names = {f.__name__ for f in skill_packs._pack_seeders()}
    assert "seed_magicpack" in seeder_names          # found by name - no seed_all edit


def test_seed_magicpack_once_even_on_all_stamps(desk_env):
    """The v0.492 once-ever law: a tenant that consumed seed AND byox AND prog AND sp AND fe
    still receives the MAGIC pack; never twice."""
    from app.coder import skill_packs, skills_store, store
    T = "mg-t1"
    store.ensure()
    store.mark_consumed(skill_packs.SEED_STAMP.format(T))
    store.mark_consumed(skill_packs.BYOX_STAMP.format(T))
    store.mark_consumed(skill_packs.PROG_STAMP.format(T))
    store.mark_consumed(skill_packs.SP_STAMP.format(T))
    store.mark_consumed(skill_packs.FE_STAMP.format(T))   # every older stamp set - mg is NOT
    r = skill_packs.seed_magicpack(T)
    assert r["mg_seeded"] == 1
    assert skill_packs.seed_magicpack(T)["mg_seeded"] == 0   # own stamp: never twice
    names = {s["name"] for s in skills_store.listing(T)}
    assert names == {"mg-21st-ui"}


def test_seed_magicpack_hers_win(desk_env):
    from app.coder import skill_packs, skills_store
    T = "mg-t2"
    skills_store.create(T, "mg-21st-ui", "Her own 21st notes", "her words")
    skill_packs.seed_magicpack(T)
    row = next(s for s in skills_store.listing(T) if s["name"] == "mg-21st-ui")
    assert row["description"] == "Her own 21st notes"


def test_magicpack_disabled_seeds_nothing(desk_env, monkeypatch):
    monkeypatch.setenv("MAGICPACK_ENABLED", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.coder import skill_packs
    assert skill_packs.seed_magicpack("mg-t3")["mg_seeded"] == 0
    get_settings.cache_clear()


def test_mg_seed_content_pins():
    """The SKILL.md distilled: search-first, the entitlement gate, the stop-law, free-tier
    honesty, the kill-switch honesty - under the 4,000-char cap."""
    from app.coder import skill_packs
    body = skill_packs.mg_files()[0].read_text(encoding="utf-8")
    fm_end = body.split("---", 2)[2] if body.count("---") >= 2 else body
    assert len(fm_end) <= 4000
    for token in ("search-first", "WORKFLOW 1", "WORKFLOW 2", "get_usage.aiGenerationEnabled",
                  "ai_subscription_required", "RUK JAO", "2 component installs/day",
                  "search_logo", "fe-ui-kit", "coder_magic21", "KABHI"):
        assert token in body, token
    assert "21st_magic_component_builder" in body    # the legacy names, named honestly


# ------------------------------------------------------------------ (9) the archive

def test_archive_rides_verbatim():
    base = REPO_ROOT / "server/app/coder/skillpack/upstream/21st-magic-mcp"
    readme = (base / "README.md").read_text(encoding="utf-8")
    assert "Magic MCP is now the 21st MCP" in readme
    assert "https://21st.dev/api/mcp" in readme
    lic = (base / "LICENSE").read_text(encoding="utf-8")
    assert "ISC License" in lic and "2026 21st.dev" in lic
    src = (base / "src/index.ts").read_text(encoding="utf-8")
    assert NOT_AUTHED_UPSTREAM in src                 # the proxy source, the protocol doc
    assert "authRefused" in src                       # the 401 latch, upstream's own
    skill = (base / "skills/21st-ui/SKILL.md").read_text(encoding="utf-8")
    assert "get_usage.aiGenerationEnabled" in skill and "search_logo" in skill
    prov = (base / "PROVENANCE.md").read_text(encoding="utf-8")
    assert "6b5299e8a83ceffa73d4fc4e148905bb3eeeeb55" in prov and "ISC" in prov
    plug = json.loads((base / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    assert plug["name"] == "21st" and plug["license"] == "ISC"
    assert (base / "server.json").exists() and (base / "mcp.json").exists()


# ------------------------------------------------------------------ desk fixture

@pytest.fixture()
def desk_env(monkeypatch, tmp_path):
    """The skills desk (the fepack suite's shape): fresh vault + store, seeding armed."""
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_SKILLS", "true")
    monkeypatch.setenv("CODER_SKILLS_SEED", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder-desk"))
    from app.config import get_settings
    from app.coder import skills_store, store
    get_settings.cache_clear()
    store.ensure()
    skills_store.reset_for_tests()
    yield monkeypatch
    skills_store.reset_for_tests()
    get_settings.cache_clear()
