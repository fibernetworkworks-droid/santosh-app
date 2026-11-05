"""HOOLA 21ST (v0.512.0) - UI components, themes and templates straight from the 21st.dev
catalog into Santosh's turn, the 21st-dev/magic-mcp port (github.com/21st-dev/magic-mcp @
6b5299e8, clone read end-to-end 2026-11-05).

What Magic MCP is now: Magic MCP is DEAD as a standalone - it is the unified **21st MCP**
(src/index.ts:11 "Magic MCP is now the 21st MCP"). The npm package @21st-dev/magic v0.2.3 is
a thin stdio<->HTTP compatibility proxy kept alive because the old install command is baked
into countless agent configs (index.ts:11-17); the real product is a plain HTTP MCP server
at https://21st.dev/api/mcp (mcp.json:3, server.json:11; env MCP_URL_21ST, index.ts:95),
authenticated with x-api-key (server.json:12-21, REQUIRED; fresh keys at 21st.dev/mcp - old
Magic console keys were reset, README "Old Magic API keys were reset"). Tool surface
(README tool table + llms-install.md + skills/21st-ui/SKILL.md):

    search          catalog search across components / themes / templates
    get_component   full code + metadata for one catalog item (paid items unlock-gated)
    generate        hosted AI UI generation with variants - LISTED ONLY when the account
                    has AI access (README "AI access"; check get_usage.aiGenerationEnabled)
    get_inspiration get_generation / get_take   (draft reads, available with AI off)
    search_logo     brand logos as ready-to-paste JSX/TSX, one brand per call
    (+ bookmarks, team libraries, profile; tools/list is entitlement-aware)

Legacy names still translate server-side (README table): 21st_magic_component_builder ->
generate, 21st_magic_component_inspiration -> get_inspiration,
21st_magic_component_refiner -> generate, logo_search -> search_logo.

THE WIRE (the proxy IS the protocol documentation - src/index.ts): one POST per JSON-RPC
message; accept "application/json, text/event-stream" (index.ts:138-146); the Mcp-Session-Id
response header from initialize is echoed on subsequent requests (index.ts:159-165); a
notification gets no write-back (index.ts:154-157, 176-177); empty body = error
(index.ts:178-182); an auth-failure body arrives with id:null and the proxy restores the
request id so strict clients can correlate (index.ts:186-196); SSE `data:` lines are a legal
reply shape (accept header, index.ts:139). The endpoint's own refusal sentence is carried
VERBATIM (index.ts:107-109) so an agent reads the same words however the refusal arrived:

    Not authenticated - your API key is missing or was reset. Get a fresh key at
    https://21st.dev/mcp and update your MCP config (x-api-key / Bearer).

THE FEED: ONE tool `magic21` with five ops (the one-tool-per-surface law, docs7 shape):

    op=list    tools/list            -> what THIS account can call (entitlement-aware)
    op=usage   get_usage             -> aiGenerationEnabled check (the generate gate)
    op=search  search {query}        -> the catalog door (SKILL.md workflow 1, step 1)
    op=get     get_component {...}   -> full code for the chosen item
    op=call    name + arguments      -> any tool by its CURRENT name (generate,
                                        get_inspiration, search_logo, ... passthrough)

THE PINNED DEVIATIONS (the campaign style - port the capability, pin the deviations):
  stateless per turn.  Upstream holds one session per proxy process (the stdio client's
                 lifetime). Hoola initializes per op (initialize -> notifications/
                 initialized -> the call; three POSTs, nothing held between turns) - no
                 stale-session class to heal, and the session echo is still honoured.
  the 401 latch.  Once the endpoint answers 401, EVERY later call this process answers
                 locally with NOT_AUTHED - zero network. Upstream learned this the hard way:
                 "the endpoint saw ~100k [initialize retries] an hour after 0.2.0 shipped,
                 from clients that could never succeed" (index.ts:146-152). Same reasoning
                 holds: the key is read at call time from config, but a mid-process key fix
                 takes a restart anyway, so the latch costs nothing honest.
  no key = no network.  The proxy answers locally when no API key was found
                 (index.ts:167-172). Same here: empty magic21_api_key -> NOT_AUTHED
                 immediately - the endpoint requires auth for discovery AND calls
                 (server.json isRequired: true), so the POST could only fail.
  ONE attempt, drop-don't-wait.  No retry, no backoff - a coder_magic21_timeout_s ceiling
                 (default 20 s) and the error comes back as a tool result. A live turn
                 cannot wait on a marketplace.
  local courtesy window.  Per-tenant rolling hour (coder_magic21_max_per_hour default 12).
                 The window counts OPS, not the three wire POSTs each op costs.
  redaction before egress.  Every string leaf of `arguments` passes strip_private +
                 redact_secrets and a 2000-char cap before it leaves the box (upstream only
                 WARNS about secrets in the skill; Hoola enforces, the docs7 law).
  the stop-law.  A result carrying `ai_subscription_required` returns ok:False with the
                 README's own instruction - do NOT retry through legacy aliases or the CLI;
                 refresh tools / reconnect after enabling AI (README "AI access",
                 SKILL.md workflow 2 step 4).
  voice never sees it.  Out of voice.VOICE_TOOL_NAMES (the docs7/delegate_task law): a
                 marketplace round-trip has no place inside a live call.
  no vault landing (yet).  Component CODE is a tool result, not a memory of her work -
                 it rides the turn, the vault stays clean. A search-cache lane may come later.

Kill switch: coder_magic21 (default OFF - outbound network surface, bake on the VPS, then
flip via one .env line + the usual restart), under the coder_enabled master. Fail-closed
into clean {"ok": False} dicts - never an exception out of the handler.
"""
from __future__ import annotations

import collections
import json
import re
import threading
import time

DEFAULT_API_URL = "https://21st.dev/api/mcp"       # mcp.json:3 / server.json:11 (env MCP_URL_21ST there)
RETURN_CAP = 6000                                  # chars handed back to the agent
ARG_STR_CAP = 2000                                 # per-string cap on outbound arguments
PROTOCOL_VERSION = "2025-03-26"                    # streamable HTTP transport generation
CLIENT_NAME = "hoola-coder"

# index.ts:107-109, verbatim - the endpoint's own refusal sentence
NOT_AUTHED = (
    "Not authenticated - your API key is missing or was reset. Get a fresh key at "
    "https://21st.dev/mcp and update your MCP config (x-api-key / Bearer).")

# README "Old tool names -> new tool names" table, carried for the agent's muscle memory
LEGACY_NAMES = {
    "21st_magic_component_builder": "generate",
    "21st_magic_component_inspiration": "get_inspiration",
    "21st_magic_component_refiner": "generate",
    "logo_search": "search_logo",
}

CURRENT_TOOLS = ("search", "get_component", "generate", "get_inspiration", "search_logo",
                 "get_usage", "get_generation", "get_take")

_AI_SUBSCRIPTION_MARKER = "ai_subscription_required"


def _settings():
    try:
        from ..config import get_settings
        return get_settings()
    except Exception:
        return None


def _cfg(attr: str, default):
    st = _settings()
    return getattr(st, attr, default) if st is not None else default


# ------------------------------------------------------------- the courtesy window

_WINDOW: dict[str, collections.deque] = {}
_WINDOW_LOCK = threading.Lock()

# the 401 latch (index.ts:146-152, the ~100k-retries lesson): process-wide, never reset
_AUTH_REFUSED = False
_AUTH_LOCK = threading.Lock()


def _window_allow(tenant: str, limit: int) -> bool:
    """Rolling one-hour per-tenant window over OPS (each op is one slot; the three wire
    POSTs it costs are the bridge's own business)."""
    if limit <= 0:
        return False
    now = time.time()
    with _WINDOW_LOCK:
        q = _WINDOW.setdefault(tenant or "-", collections.deque())
        while q and now - q[0] > 3600.0:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


def _window_reset() -> None:
    """Test seam."""
    with _WINDOW_LOCK:
        _WINDOW.clear()


def _latch_refused() -> bool:
    global _AUTH_REFUSED
    with _AUTH_LOCK:
        return _AUTH_REFUSED


def _latch_trip() -> None:
    global _AUTH_REFUSED
    with _AUTH_LOCK:
        _AUTH_REFUSED = True


def _reset_auth_latch() -> None:
    """Test seam (upstream has none - a proxy process never re-reads its key; tests do)."""
    global _AUTH_REFUSED
    with _AUTH_LOCK:
        _AUTH_REFUSED = False


# ------------------------------------------------------------- redaction before egress

def _redact_query(text: str) -> str:
    """The search-query pass: strip private blocks, mask secrets, collapse whitespace, trim
    (the docs7.redact_query twin - a catalog query is one line of intent)."""
    from .redact import redact_secrets, strip_private
    t = strip_private(str(text or ""))
    t = redact_secrets(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:ARG_STR_CAP]


def _redact_leaf(text: str) -> str:
    """The argument-leaf pass: strip private blocks, mask secrets, cap length - NO whitespace
    collapse (generate briefs and component snippets carry code; the formatting is hers)."""
    from .redact import redact_secrets, strip_private
    t = strip_private(str(text or ""))
    t = redact_secrets(t)
    return t[:ARG_STR_CAP]


def redact_arguments(args) -> dict:
    """Deep-redact every string leaf of the outbound arguments (upstream WARNS in the skill;
    Hoola enforces - the docs7 law extended to a JSON tree)."""
    if isinstance(args, dict):
        return {k: redact_arguments(v) for k, v in args.items()}
    if isinstance(args, list):
        return [redact_arguments(v) for v in args]
    if isinstance(args, str):
        return _redact_leaf(args)
    return args


# ------------------------------------------------------------- the wire (the ONE seam)

def _headers(api_key: str, session_id: str | None) -> dict:
    # index.ts:138-146: content-type, accept, user-agent, x-api-key, mcp-session-id
    h = {"content-type": "application/json",
         "accept": "application/json, text/event-stream",
         "user-agent": f"{CLIENT_NAME}/0.512.0"}
    if api_key:
        h["x-api-key"] = api_key
    if session_id:
        h["mcp-session-id"] = session_id
    return h


async def _http(url: str, headers: dict, body: str, timeout: float) -> tuple[int, dict, str]:
    """The ONE network seam (tests monkeypatch this). One attempt - drop-don't-wait.
    Returns (status, response-headers-of-interest, text)."""
    import httpx
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as c:
        r = await c.post(url, headers=headers, content=body)
        keep = {}
        sid = r.headers.get("mcp-session-id")
        if sid:
            keep["mcp-session-id"] = sid
        return r.status_code, keep, r.text


def _parse_reply(text: str):
    """JSON first, then the SSE `data:` shape (accept header, index.ts:139); None when neither."""
    t = (text or "").strip()
    if not t:
        return None
    try:
        return json.loads(t)
    except Exception:
        pass
    chunks: list[str] = []
    for line in t.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            chunks.append(line[5:].strip())
    if not chunks:
        return None
    for raw in reversed(chunks):
        try:
            return json.loads(raw)
        except Exception:
            continue
    return None


def _rpc(id_: int, method: str, params: dict | None) -> str:
    msg: dict = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        msg["params"] = params
    return json.dumps(msg)


def _rpc_error(id_, code: int, message: str) -> dict:
    return {"ok": False, "error": message, "code": code}


def _result_text(parsed) -> tuple[bool, str, dict]:
    """(ok, text, payload) out of a tools/call reply. An MCP error dict and a tool-level
    error both land here honestly; content blocks join as text."""
    if not isinstance(parsed, dict):
        return False, "21st MCP returned a non-JSON reply", {}
    if isinstance(parsed.get("error"), dict):
        err = parsed["error"]
        return False, str(err.get("message") or err), {}
    res = parsed.get("result")
    if not isinstance(res, dict):
        return False, "21st MCP returned no result", {}
    blocks = res.get("content") or []
    texts = []
    for b in blocks:
        if isinstance(b, dict) and b.get("type") == "text":
            texts.append(str(b.get("text") or ""))
    text = "\n".join(x for x in texts if x)
    return True, text, res


# ------------------------------------------------------------- the bridge core

async def _call_tool(op_name: str, name: str, arguments: dict, tenant: str) -> dict:
    """initialize -> notifications/initialized -> tools/call. Stateless per turn (the
    pinned deviation); the session echo honoured within the turn (index.ts:159-165)."""
    base = str(_cfg("magic21_api_url", DEFAULT_API_URL) or DEFAULT_API_URL).strip()
    key = str(_cfg("magic21_api_key", "") or "").strip()
    timeout = float(_cfg("coder_magic21_timeout_s", 20) or 20)
    if not key:
        return _rpc_error(None, -32001, NOT_AUTHED)          # index.ts:167-172, locally
    if _latch_refused():
        return _rpc_error(None, -32001, NOT_AUTHED)          # the latch: zero network
    try:
        st, hd, body = await _http(base, _headers(key, None),
                                   _rpc(1, "initialize", {
                                       "protocolVersion": PROTOCOL_VERSION,
                                       "capabilities": {},
                                       "clientInfo": {"name": CLIENT_NAME, "version": "0.512.0"},
                                   }), timeout)
    except Exception as e:
        return {"ok": False, "error": f"21st MCP unreachable ({base}): "
                                      f"{type(e).__name__}: {str(e)[:200]}"}
    if st == 401:
        _latch_trip()                                        # index.ts:169
        return _rpc_error(None, -32001, NOT_AUTHED)
    if st != 200:
        return _rpc_error(None, -32000, f"initialize failed with HTTP {st}: {body[:200]}")
    parsed = _parse_reply(body)
    if parsed is None:
        return _rpc_error(None, -32000, f"Empty response (HTTP {st})")   # index.ts:178-182 wording
    session_id = hd.get("mcp-session-id")
    # the initialized notification - no reply expected (index.ts:154-157)
    try:
        await _http(base, _headers(key, session_id),
                    json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                    timeout)
    except Exception:
        pass                                                 # a notification may not fail the turn
    try:
        st, hd2, body = await _http(base, _headers(key, session_id),
                                    _rpc(2, "tools/call", {"name": name, "arguments": arguments}),
                                    timeout)
    except Exception as e:
        return {"ok": False, "error": f"21st MCP unreachable ({base}): "
                                      f"{type(e).__name__}: {str(e)[:200]}"}
    if st == 401:
        _latch_trip()
        return _rpc_error(None, -32001, NOT_AUTHED)
    if st != 200:
        return _rpc_error(None, -32000, f"tools/call failed with HTTP {st}: {body[:200]}")
    parsed = _parse_reply(body)
    if parsed is None:
        return _rpc_error(None, -32000, f"Empty response (HTTP {st})")
    # index.ts:186-196: an auth-failure body arrives with id:null; the request id rides back
    if isinstance(parsed, dict) and parsed.get("id") is None and "error" in parsed:
        if isinstance(parsed.get("error"), dict) and str(parsed["error"].get("code")) == "-32001":
            return _rpc_error(None, -32001, str(parsed["error"].get("message") or NOT_AUTHED))
    ok, text, res = _result_text(parsed)
    if ok and _AI_SUBSCRIPTION_MARKER in text:
        # README "AI access" + SKILL.md workflow 2 step 4: stop, never retry through aliases
        return {"ok": False,
                "error": ("ai_subscription_required - hosted AI is not enabled on this account. "
                          "Stop generation attempts (legacy aliases and the CLI included). "
                          "After enabling AI, refresh the tool list or reconnect before trying "
                          "again. get_usage.aiGenerationEnabled reports access, not the "
                          "remaining credit balance."),
                "raw": text[:RETURN_CAP]}
    if ok:
        return {"ok": True, "text": text[:RETURN_CAP], "tool": name,
                "is_error": bool(res.get("isError"))}
    return {"ok": False, "error": text[:RETURN_CAP] or "21st MCP returned no result", "tool": name}


async def _list_tools(tenant: str) -> dict:
    """tools/list - what THIS account can call (the entitlement-aware discovery door)."""
    base = str(_cfg("magic21_api_url", DEFAULT_API_URL) or DEFAULT_API_URL).strip()
    key = str(_cfg("magic21_api_key", "") or "").strip()
    timeout = float(_cfg("coder_magic21_timeout_s", 20) or 20)
    if not key:
        return _rpc_error(None, -32001, NOT_AUTHED)
    if _latch_refused():
        return _rpc_error(None, -32001, NOT_AUTHED)
    try:
        st, hd, body = await _http(base, _headers(key, None),
                                   _rpc(1, "initialize", {
                                       "protocolVersion": PROTOCOL_VERSION,
                                       "capabilities": {},
                                       "clientInfo": {"name": CLIENT_NAME, "version": "0.512.0"},
                                   }), timeout)
    except Exception as e:
        return {"ok": False, "error": f"21st MCP unreachable ({base}): "
                                      f"{type(e).__name__}: {str(e)[:200]}"}
    if st == 401:
        _latch_trip()
        return _rpc_error(None, -32001, NOT_AUTHED)
    if st != 200:
        return _rpc_error(None, -32000, f"initialize failed with HTTP {st}: {body[:200]}")
    parsed = _parse_reply(body)
    if parsed is None:
        return _rpc_error(None, -32000, f"Empty response (HTTP {st})")
    session_id = hd.get("mcp-session-id")
    try:
        await _http(base, _headers(key, session_id),
                    json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}), timeout)
    except Exception:
        pass
    try:
        st, _hd2, body = await _http(base, _headers(key, session_id),
                                     _rpc(2, "tools/list", {}), timeout)
    except Exception as e:
        return {"ok": False, "error": f"21st MCP unreachable ({base}): "
                                      f"{type(e).__name__}: {str(e)[:200]}"}
    if st == 401:
        _latch_trip()
        return _rpc_error(None, -32001, NOT_AUTHED)
    if st != 200:
        return _rpc_error(None, -32000, f"tools/list failed with HTTP {st}: {body[:200]}")
    parsed = _parse_reply(body)
    if parsed is None:
        return _rpc_error(None, -32000, f"Empty response (HTTP {st})")
    res = parsed.get("result") if isinstance(parsed, dict) else None
    tools = (res or {}).get("tools") or []
    names = [str(t.get("name") or "") for t in tools if isinstance(t, dict)]
    lines = []
    for t in tools:
        if isinstance(t, dict):
            lines.append(f"- {t.get('name', '')}: {' '.join(str(t.get('description') or '').split())[:200]}")
    text = ("21st MCP tools available to this account (tools/list is entitlement-aware - "
            "`generate` appears only when hosted AI access is on):\n" + "\n".join(lines)) if lines \
        else "No tools returned for this account."
    return {"ok": True, "text": text[:RETURN_CAP], "tools": names, "generate_listed": "generate" in names}


# ------------------------------------------------------------- the ONE tool

MAGIC21_SCHEMA = {
    "name": "magic21",
    "description": (
        "Search the 21st.dev catalog (10,000+ production-ready React/Tailwind "
        "shadcn-compatible components, themes, templates), fetch a component's full code, "
        "and - only when the account has hosted AI access - generate new UI. The 21st MCP "
        "(formerly Magic MCP) bridge. FIVE ops: op=list = tools/list, the entitlement-aware "
        "discovery door; op=usage = get_usage (aiGenerationEnabled reports ACCESS, not "
        "credit balance); op=search {query} = short natural catalog search, ONE thing per "
        "query; op=get {arguments} = get_component, full code + metadata for one item; "
        "op=call {name, arguments} = any tool by its CURRENT name (search, get_component, "
        "generate, get_inspiration, search_logo, get_generation, get_take - legacy names "
        "21st_magic_component_builder/inspiration/refiner and logo_search translate, but "
        "prefer the new ones). THE LAW: prefer real catalog components over writing UI from "
        "scratch; BEFORE any generate, check op=usage - missing/unknown AI status is NOT "
        "permission to generate; a result carrying ai_subscription_required means STOP, no "
        "retries through aliases or the CLI. Free tier: catalog search + 2 installs/day; "
        "paid components return code only after unlock - say so honestly. NEVER put secrets "
        "in arguments - they are redacted before leaving the box. One marketplace round "
        "trip per question - never chain calls mid-answer."),
    "input_schema": {
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["list", "usage", "search", "get", "call"],
                   "description": "list = discovery; usage = AI-entitlement check; "
                                  "search = catalog query; get = get_component; call = any tool"},
            "query": {"type": "string",
                      "description": "op=search only: short natural query ('pricing table', "
                                     "'animated hero') - one thing per query"},
            "name": {"type": "string",
                     "description": "op=call only: the tool's CURRENT name (search, "
                                    "get_component, generate, get_inspiration, search_logo, "
                                    "get_usage, get_generation, get_take)"},
            "arguments": {"type": "object",
                          "description": "op=get / op=call: the tool's arguments as a JSON "
                                         "object (string leaves are redacted before egress)"},
        },
        "required": ["op"],
    },
}

MAGIC21_TOOLS = [MAGIC21_SCHEMA]
MAGIC21_LABELS = {"magic21": "21st.dev ke catalog se UI components dhoond rahi hoon"}
MAGIC21_HANDLERS: dict = {"magic21": None}                 # set below


async def magic21(ctx, op: str = "list", query: str = "", name: str = "",
                  arguments=None, **_):
    """The one 21st.dev surface. Gates -> redact -> one op -> clean dict. Fail-closed."""
    st = _settings()
    if not getattr(st, "coder_enabled", True):
        return {"ok": False, "error": "coder memory is switched off (coder_enabled)"}
    if not getattr(st, "coder_magic21", False):
        return {"ok": False, "error": "magic21 is switched off (coder_magic21) - bake, then flip"}
    tenant = getattr(ctx, "tenant_id", "-") or "-"
    op = str(op or "").strip().lower()

    if op == "list":
        if not _window_allow(tenant, int(_cfg("coder_magic21_max_per_hour", 12) or 12)):
            return {"ok": False,
                    "error": ("magic21 courtesy window reached for this hour "
                              "(coder_magic21_max_per_hour) - ask again later.")}
        return await _list_tools(tenant)

    if op == "usage":
        if not _window_allow(tenant, int(_cfg("coder_magic21_max_per_hour", 12) or 12)):
            return {"ok": False,
                    "error": ("magic21 courtesy window reached for this hour "
                              "(coder_magic21_max_per_hour) - ask again later.")}
        return await _call_tool("usage", "get_usage", {}, tenant)

    if op == "search":
        q = _redact_query(query)
        if not q:
            return {"ok": False, "error": "query is required for op=search (short and natural, "
                                          "e.g. 'pricing table')"}
        if not _window_allow(tenant, int(_cfg("coder_magic21_max_per_hour", 12) or 12)):
            return {"ok": False,
                    "error": ("magic21 courtesy window reached for this hour "
                              "(coder_magic21_max_per_hour) - ask again later.")}
        return await _call_tool("search", "search", {"query": q}, tenant)

    if op in ("get", "call"):
        tool_name = str(name or "").strip()
        if op == "get":
            tool_name = "get_component"
            if not isinstance(arguments, dict) or not arguments:
                return {"ok": False,
                        "error": ("op=get needs the item's arguments (install id / slug from "
                                  "an op=search result) in `arguments`")}
        if not tool_name:
            return {"ok": False, "error": "op=call needs the tool's CURRENT name in `name`"}
        tool_name = LEGACY_NAMES.get(tool_name, tool_name)   # README translation table
        if not isinstance(arguments, dict):
            arguments = {}
        args = redact_arguments(arguments)
        if not _window_allow(tenant, int(_cfg("coder_magic21_max_per_hour", 12) or 12)):
            return {"ok": False,
                    "error": ("magic21 courtesy window reached for this hour "
                              "(coder_magic21_max_per_hour) - ask again later.")}
        return await _call_tool("call", tool_name, args, tenant)

    return {"ok": False, "error": ("unknown op - use 'list', 'usage', 'search', 'get' or "
                                   "'call'")}


MAGIC21_HANDLERS["magic21"] = magic21
