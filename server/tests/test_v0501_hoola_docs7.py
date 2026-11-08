"""v0.510.0 HOOLA CONTEXT7 - the upstash/context7 port (owner: 'FEED CONTEXT7 TO HOOLA'). The
repo was read end-to-end first (upstash/context7 @ 193e4bb, @upstash/context7-mcp v4.5.0);
this suite pins the port against upstream's own file:line facts:

(1) TOOL SHAPE: ONE docs7 tool, two ops (resolve/query) - the skill_manage/delegate_task law.
(2) RESOLVE FORMATTING: byte-faithful to upstream formatSearchResult (utils.ts:22-84) -
    reputation >=7 High / >=4 Medium / else Low / negative-or-None Unknown, Code Snippets hidden
    when -1 or missing, Benchmark Score only when > 0, Versions comma-joined, Source appended,
    results joined with the ---------- divider, prefixed "Available Libraries:".
(3) QUERY: GET {base}/v2/context?query&libraryId[&language]; empty body = a VALID not-found
    answer (api.ts:231-243), never an error; 429/404/401 messages ported verbatim (api.ts:44-52).
(4) THE VAULT IS THE CACHE: a fresh (within coder_docs7_ttl_hours) library+query answers from
    the vault with ZERO network; a post-TTL re-fetch REFRESHES the docs7 row in place (docs are
    living rows - the only narrative-updating writer in the coder); tenant-scoped lookups.
(5) REDACTION BEFORE EGRESS: the query passes strip_private + redact_secrets BEFORE the mock
    network ever sees it (upstream warns; Hoola enforces).
(6) VOICE-BOX CAPS: one attempt drop-don't-wait (a raised _http = clean error, no retry), a
    per-tenant rolling-hour window (cache hits are free and never counted).
(7) KILL SWITCHES: coder_docs7 default OFF, coder_enabled master - both fail-closed with NO
    network call.
(8) WIRING: package export (the v0.478 lesson), agent/tools.py mount, voice absence, config
    defaults, APP_VERSION + pubspec pins.
Every network test rides the ONE seam (docs7._http) - no test touches the real network.
"""
import json
import re
import time

import pytest

REPO_ROOT = pytest.importorskip("pathlib").Path(__file__).resolve().parents[2]

T, CONV = "tenant-docs7", "conv-docs7"


def _ctx(tenant=T):
    return type("C", (), {"tenant_id": tenant, "conversation_id": CONV})()


def _call(*args, **kw):
    """The house async-call pattern (asyncio.run, the swarm/selfteach suites' shape)."""
    import asyncio
    from app.coder import docs7
    return asyncio.run(docs7.docs7(*args, **kw))


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """Fresh vault in a TEMP dir, docs7 ON, window generous unless a test shrinks it."""
    monkeypatch.setenv("CODER_ENABLED", "true")
    monkeypatch.setenv("CODER_DOCS7", "true")
    monkeypatch.setenv("CODER_DIR", str(tmp_path / "coder"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app.coder import docs7, store
    store.ensure()
    docs7._window_reset()
    yield monkeypatch
    docs7._window_reset()
    get_settings.cache_clear()


class _Spy:
    """The ONE network seam, faked: records every call, replays a scripted response."""

    def __init__(self, status=200, body=""):
        self.status, self.body = status, body
        self.calls: list[dict] = []
        self.params_seen: dict = {}

    async def __call__(self, url, headers, params, timeout):
        self.calls.append({"url": url, "headers": dict(headers), "params": dict(params),
                           "timeout": timeout})
        self.params_seen.update(dict(params))
        return self.status, self.body


def _bomb():
    async def _no_network(*a, **k):
        raise AssertionError("network called - this path must be offline")
    return _no_network


def _docs7_rows(tenant=T):
    from app.coder import store
    with store.db() as c:
        return [dict(r) for r in c.execute(
            "SELECT id, tenant, type, title, narrative FROM observations "
            "WHERE tenant=? AND type='docs7' ORDER BY id", (tenant,)).fetchall()]


# ------------------------------------------------------------------ (1) shape + wiring

def test_one_tool_two_ops_shape(env):
    from app.coder import docs7
    assert [t["name"] for t in docs7.DOCS7_TOOLS] == ["docs7"]
    sch = docs7.DOCS7_SCHEMA["input_schema"]
    assert sch["properties"]["op"]["enum"] == ["resolve", "query"]
    assert set(docs7.DOCS7_HANDLERS) == {"docs7"} and docs7.DOCS7_HANDLERS["docs7"] is docs7.docs7
    # the upstream discipline lives in the description (index.ts:344-371, 438-446, 458-463)
    d = docs7.DOCS7_SCHEMA["description"]
    assert "resolve" in d and "/org/project" in d and "Max 3" in d and "NEVER" in d


def test_registry_mount(env):
    from app.agent import tools
    assert "docs7" in tools.HANDLERS and "docs7" in tools.TOOL_LABELS
    assert any(t["name"] == "docs7" for t in tools.TOOLS)


def test_voice_absence(env):
    """A 20s network stall has no place in a live call - voice never sees docs7 (the
    delegate_task precedent)."""
    from app import voice
    assert "docs7" not in voice.VOICE_TOOL_NAMES


def test_package_export(env):
    """The v0.478 funnel lesson: coder.docs7 must exist on the PACKAGE path."""
    from app import coder
    assert hasattr(coder, "docs7") and "docs7" in coder.__all__
    assert callable(coder.docs7.op_resolve) and callable(coder.docs7.op_query)


def test_config_defaults(env):
    """The DEFAULTS, read with the fixture's opt-in removed (the deployment opts in, not config.py)."""
    env.delenv("CODER_DOCS7", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    st = get_settings()
    assert st.coder_docs7 is False                      # default OFF - the deployment opts in
    assert st.context7_api_url == "https://context7.com/api"   # upstream constants.ts:14
    assert st.context7_api_key == ""                    # BYOK, never in chat
    assert st.coder_docs7_timeout_s == 20               # upstream 60s; the voice box drops
    assert st.coder_docs7_max_per_hour == 12 and st.coder_docs7_ttl_hours == 168


def test_version(env):
    from app.main import APP_VERSION
    assert APP_VERSION == "0.687.0"
    # v0.535: was pinned to a literal version, in a spelling the version ritual does not rewrite, so it broke on every
    # bump by any session. Its real job is that main.py and pubspec agree - which is what it now checks.
    _v = re.search(r'APP_VERSION = "([0-9.]+)"', (REPO_ROOT / "server" / "app" / "main.py").read_text()).group(1)
    assert f"version: {_v}+" in (REPO_ROOT / "pubspec.yaml").read_text(), f"pubspec must carry {_v}"


# ------------------------------------------------------------------ (2) resolve formatting

def test_resolve_formats_like_upstream(env, monkeypatch):
    """utils.ts:22-84 byte-faithful: the exact field order, the divider, the prefix."""
    from app.coder import docs7
    body = {"results": [{
        "id": "/vercel/next.js", "title": "Next.js", "description": "The React framework",
        "totalSnippets": 1421, "trustScore": 9, "benchmarkScore": 95,
        "versions": ["v15", "v16"], "source": "github"}]}
    spy = _Spy(body=json.dumps(body))
    monkeypatch.setattr(docs7, "_http", spy)
    out = _call(_ctx(), op="resolve", query="app router proxy", library_name="Next.js")
    assert out["ok"] is True
    assert out["text"].startswith("Available Libraries:\n\n")
    assert "- Title: Next.js" in out["text"]
    assert "- Context7-compatible library ID: /vercel/next.js" in out["text"]
    assert "- Code Snippets: 1421" in out["text"]
    assert "- Source Reputation: High" in out["text"]
    assert "- Benchmark Score: 95" in out["text"]
    assert "- Versions: v15, v16" in out["text"]
    assert "- Source: github" in out["text"]
    assert spy.calls and spy.calls[0]["url"].endswith("/v2/libs/search")
    assert spy.calls[0]["params"]["libraryName"] == "Next.js"


def test_reputation_thresholds(env):
    """utils.ts:7-14 verbatim: >=7 High, >=4 Medium, else Low; None/negative -> Unknown."""
    from app.coder import docs7
    assert docs7._reputation(9) == "High" and docs7._reputation(7) == "High"
    assert docs7._reputation(4) == "Medium" and docs7._reputation(6) == "Medium"
    assert docs7._reputation(2) == "Low"
    assert docs7._reputation(None) == "Unknown" and docs7._reputation(-1) == "Unknown"


def test_snippets_hidden_at_minus_one_and_bench_at_zero(env):
    from app.coder import docs7
    line = docs7.format_search_result({"id": "/a/b", "title": "T", "description": "d",
                                       "totalSnippets": -1, "benchmarkScore": 0})
    assert "Code Snippets" not in line and "Benchmark Score" not in line
    assert "Source Reputation: Unknown" in line          # no trustScore -> Unknown


def test_resolve_empty_wording(env, monkeypatch):
    """index.ts:410-413: an empty match is NOT an error and uses upstream's exact wording."""
    from app.coder import docs7
    monkeypatch.setattr(docs7, "_http", _Spy(body='{"results": []}'))
    out = _call(_ctx(), op="resolve", query="q", library_name="Nonexistent Lib")
    assert out["ok"] is True
    assert out["text"] == "No libraries found matching the provided name."


def test_resolve_requires_name(env, monkeypatch):
    from app.coder import docs7
    monkeypatch.setattr(docs7, "_http", _bomb())
    out = _call(_ctx(), op="resolve", query="q", library_name="  ")
    assert out["ok"] is False and "library_name" in out["error"]


def test_error_429_no_key_verbatim(env, monkeypatch):
    """api.ts:50-51 port: an anonymous 429 sends the free-API-key wording."""
    from app.coder import docs7
    monkeypatch.setattr(docs7, "_http", _Spy(status=429, body=""))
    out = _call(_ctx(), op="resolve", query="q", library_name="Next.js")
    assert out["ok"] is False
    assert out["error"] == ("Rate limited or quota exceeded. Create a free API key at "
                            "https://context7.com/dashboard for higher limits.")


def test_error_404_and_401_verbatim(env, monkeypatch):
    """api.ts:52-53 ports, on the query op."""
    from app.coder import docs7
    monkeypatch.setattr(docs7, "_http", _Spy(status=404, body=""))
    out = _call(_ctx(), op="query", query="q", library_id="/no/such-lib")
    assert out["ok"] is False
    assert out["error"] == ("The library you are trying to access does not exist. Please try "
                            "with a different library ID.")
    monkeypatch.setattr(docs7, "_http", _Spy(status=401, body=""))
    out = _call(_ctx(), op="query", query="q", library_id="/a/b")
    assert out["ok"] is False
    assert out["error"] == ("Invalid API key. Please check your API key. API keys should start "
                            "with 'ctx7sk' prefix.")


def test_api_json_message_wins(env, monkeypatch):
    """api.ts:47-48: the API's own message beats the status wording."""
    from app.coder import docs7
    monkeypatch.setattr(docs7, "_http", _Spy(status=429, body='{"message": "custom upstream msg"}'))
    out = _call(_ctx(), op="resolve", query="q", library_name="Next.js")
    assert out["error"] == "custom upstream msg"


# ------------------------------------------------------------------ (3) the query op

def test_query_requires_library_id(env, monkeypatch):
    """The resolve-first law (index.ts:447-449): a bare name is not an ID."""
    from app.coder import docs7
    monkeypatch.setattr(docs7, "_http", _bomb())
    out = _call(_ctx(), op="query", query="q", library_id="next.js")
    assert out["ok"] is False and out["error"].startswith("Pass a Context7 library ID")


def test_query_lands_in_vault(env, monkeypatch):
    """Every successful fetch becomes a docs7 observation: title, narrative, tenant, URL."""
    from app.coder import docs7
    spy = _Spy(body="Use the App Router middleware for JWT checks.")
    monkeypatch.setattr(docs7, "_http", spy)
    out = _call(_ctx(), op="query", query="app router middleware",
                      library_id="/vercel/next.js")
    assert out["ok"] is True and out["cached"] is False
    assert spy.calls[0]["url"].endswith("/v2/context")
    assert spy.calls[0]["params"]["libraryId"] == "/vercel/next.js"
    rows = _docs7_rows()
    assert len(rows) == 1 and rows[0]["tenant"] == T
    assert rows[0]["title"] == "Context7 /vercel/next.js: app router middleware"
    assert rows[0]["narrative"] == "Use the App Router middleware for JWT checks."


def test_query_returns_capped(env, monkeypatch):
    """The agent gets RETURN_CAP chars; the vault keeps the store's 8000-char narrative cap."""
    from app.coder import docs7
    monkeypatch.setattr(docs7, "_http", _Spy(body="x" * 9000))
    out = _call(_ctx(), op="query", query="big page", library_id="/a/b")
    assert out["ok"] is True and len(out["text"]) == docs7.RETURN_CAP
    assert out["chars"] == 9000
    assert len(_docs7_rows()[0]["narrative"]) == 8000


def test_vault_cache_hit_zero_network(env, monkeypatch):
    """THE VAULT IS THE CACHE: the repeat answers from the vault with the network SEALED OFF;
    another tenant's identical query is a miss (tenant-scoped lookups)."""
    from app.coder import docs7
    monkeypatch.setattr(docs7, "_http", _Spy(body="cached docs body"))
    first = _call(_ctx(), op="query", query="jwt setup", library_id="/a/b")
    assert first["ok"] is True and first["cached"] is False
    monkeypatch.setattr(docs7, "_http", _bomb())
    second = _call(_ctx(), op="query", query="jwt setup", library_id="/a/b")
    assert second["ok"] is True and second["cached"] is True
    assert second["text"] == "cached docs body" and second["obs_id"] == first["obs_id"]
    other = _call(_ctx(tenant="tenant-other"), op="query", query="jwt setup",
                        library_id="/a/b")
    assert other["ok"] is False and "unreachable" in other["error"]   # AssertionError from _bomb
    assert len(_docs7_rows("tenant-other")) == 0                       # ...and nothing stored for it


def test_post_ttl_refetch_refreshes_row(env, monkeypatch):
    """DOCS ARE LIVING ROWS: past the TTL the re-fetch refreshes the SAME row in place -
    one row, fresh narrative, no Tier-0 ghost with year-old text."""
    from app.coder import docs7, store
    monkeypatch.setattr(docs7, "_http", _Spy(body="year-old docs"))
    _call(_ctx(), op="query", query="jwt setup", library_id="/a/b")
    with store.db(write=True) as c:
        c.execute("UPDATE observations SET created_epoch=? WHERE type='docs7'",
                  (int(time.time()) - 200 * 3600,))          # 200h > the 168h TTL
    monkeypatch.setattr(docs7, "_http", _Spy(body="fresh docs from upstream"))
    out = _call(_ctx(), op="query", query="jwt setup", library_id="/a/b")
    assert out["ok"] is True and out["cached"] is False
    rows = _docs7_rows()
    assert len(rows) == 1 and rows[0]["narrative"] == "fresh docs from upstream"


def test_redaction_before_egress(env, monkeypatch):
    """Upstream warns; Hoola enforces: the secret NEVER crosses the seam - the outbound param
    and the stored title both carry the mask, never the value."""
    from app.coder import docs7
    spy = _Spy(body="docs")
    monkeypatch.setattr(docs7, "_http", spy)
    out = _call(_ctx(), op="query", query="deploy with password=hunter2secret please",
                      library_id="/a/b")
    assert out["ok"] is True
    sent = spy.calls[0]["params"]["query"]
    assert "hunter2secret" not in sent and "***redacted***" in sent
    assert "hunter2secret" not in _docs7_rows()[0]["title"]


def test_query_timeout_drop(env, monkeypatch):
    """ONE attempt, drop-don't-wait: a raised seam becomes a clean error, no retry storm."""
    import httpx
    from app.coder import docs7

    async def _hang(url, headers, params, timeout):
        raise httpx.ConnectTimeout("timed out")
    monkeypatch.setattr(docs7, "_http", _hang)
    out = _call(_ctx(), op="query", query="q", library_id="/a/b")
    assert out["ok"] is False and "unreachable" in out["error"] and "ConnectTimeout" in out["error"]


def test_empty_body_is_valid_not_found(env, monkeypatch):
    """api.ts:231-243: an empty body is a valid not-found ANSWER (ok=True), nothing stored."""
    from app.coder import docs7
    monkeypatch.setattr(docs7, "_http", _Spy(body=""))
    out = _call(_ctx(), op="query", query="q", library_id="/a/b")
    assert out["ok"] is True and "Documentation not found or not finalized" in out["text"]
    assert "resolve-library-id" in out["text"]           # the upstream guidance, verbatim
    assert _docs7_rows() == []


# ------------------------------------------------------------------ (4) the courtesy window

def test_courtesy_window(env, monkeypatch):
    """coder_docs7_max_per_hour bounds the NETWORK calls (misses only); the message names the knob."""
    from app.config import get_settings
    from app.coder import docs7
    monkeypatch.setenv("CODER_DOCS7_MAX_PER_HOUR", "2")
    get_settings.cache_clear()
    monkeypatch.setattr(docs7, "_http", _Spy(body="docs"))
    for i in range(2):
        out = _call(_ctx(), op="query", query=f"question {i}", library_id=f"/a/b{i}")
        assert out["ok"] is True, out
    third = _call(_ctx(), op="query", query="question 3", library_id="/a/b3")
    assert third["ok"] is False and "courtesy window" in third["error"]


def test_cache_hit_never_counted(env, monkeypatch):
    """A vault hit is free: with a window of 1, the repeat still answers, a new topic is refused."""
    from app.config import get_settings
    from app.coder import docs7
    monkeypatch.setenv("CODER_DOCS7_MAX_PER_HOUR", "1")
    get_settings.cache_clear()
    monkeypatch.setattr(docs7, "_http", _Spy(body="body A"))
    first = _call(_ctx(), op="query", query="topic a", library_id="/a/1")
    assert first["ok"] is True and first["cached"] is False
    again = _call(_ctx(), op="query", query="topic a", library_id="/a/1")
    assert again["ok"] is True and again["cached"] is True          # free, network sealed anyway
    blocked = _call(_ctx(), op="query", query="topic b", library_id="/a/2")
    assert blocked["ok"] is False and "courtesy window" in blocked["error"]


def test_language_forwarded(env, monkeypatch):
    """index.ts:473-476: language ranks matching code examples first."""
    from app.coder import docs7
    spy = _Spy(body="docs")
    monkeypatch.setattr(docs7, "_http", spy)
    _call(_ctx(), op="query", query="q", library_id="/a/b", language="Python")
    assert spy.params_seen.get("language") == "Python"


def test_unknown_op(env, monkeypatch):
    from app.coder import docs7
    monkeypatch.setattr(docs7, "_http", _bomb())
    out = _call(_ctx(), op="bogus", query="q")
    assert out["ok"] is False and "resolve" in out["error"] and "query" in out["error"]
