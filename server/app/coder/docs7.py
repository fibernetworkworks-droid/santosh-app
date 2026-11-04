"""HOOLA CONTEXT7 (v0.501.0) - up-to-date library documentation straight into Santosh's context,
the upstash/context7 port (github.com/upstash/context7 @ 193e4bb, @upstash/context7-mcp v4.5.0).

What Context7 is: an MCP server + API that pulls CURRENT, version-specific documentation and
code examples for any library, so an agent stops hallucinating APIs from year-old training
data. Its whole product surface is two tools (packages/mcp/src/lib/tool-names.ts:1-10):

    resolve-library-id   GET {base}/v2/libs/search?query=&libraryName=      (api.ts:142-146)
    query-docs           GET {base}/v2/context?query=&libraryId=&language=  (api.ts:214-218)

with base = https://context7.com/api (constants.ts:14), auth = optional "Authorization: Bearer
ctx7sk-..." (encryption.ts:72; keys carry the ctx7sk prefix - sdk/src/client.ts:26), a 60 s
ceiling on every upstream call (api.ts:23; their comment: p99.9 ~3.2 s), and error semantics
429 rate limited / 404 no such library / 401 invalid key (api.ts:44-52).

THE FEED: ONE tool `docs7` with two ops (the skill_manage/delegate_task law - one tool per
surface). The output formatting is byte-faithful to upstream's formatSearchResult
(packages/mcp/src/lib/utils.ts:22-84): reputation trustScore >=7 High / >=4 Medium / else Low
(undefined or negative -> Unknown), Code Snippets hidden when -1 or missing, Benchmark Score
shown only when > 0, Versions comma-joined, Source appended, results joined with a
"----------" divider line, the list prefixed "Available Libraries:". Every successful fetch
lands in the vault as a docs7 observation, so the machinery that remembers her work also
remembers the docs: FTS5 search, the session-start primer, the dedup ladder and the curator's
weekly consolidation all see the same rows. THE VAULT IS THE CACHE: the same library+query
inside coder_docs7_ttl_hours (default a week) is answered from the vault with ZERO network -
upstream's SDK defaults to no-store, but a voice box burns no quota re-reading what it kept.

THE PINNED DEVIATIONS (voice-box law; each a deliberate departure from upstream, the campaign
style - port the capability, pin the deviations):
  ONE attempt, drop-don't-wait.  The upstream SDK retries 5x with exponential backoff on
                 {408,425,429,500,502,503,504} and honours Retry-After (sdk/src/http/
                 retry.ts:3,27-34) - right for an infrastructure process, wrong for a live
                 turn. Hoola fires ONCE with a coder_docs7_timeout_s ceiling (default 20 s vs
                 their 60 s) and returns the error as a tool result.
  local courtesy window.  Upstream rate-limits server-side (the 429 message is ported
                 verbatim); Hoola ALSO keeps a per-tenant rolling-hour window
                 (coder_docs7_max_per_hour default 12) so a confused turn cannot stampede the
                 API. The "<= 3 calls per question" law from upstream's tool descriptions
                 (index.ts:371, 445) lives in the schema description AND in this window.
  redaction before egress.  Upstream WARNS "do not include sensitive or confidential
                 information in your query" (index.ts:358-360, 462-463). Hoola warns AND
                 enforces: the query passes the vault's strip_private + redact_secrets before
                 it leaves the box, and the redacted form is what gets sent AND stored.
  docs are living rows.  A docs7 observation mirrors an upstream page, not a memory of an
                 event. So a post-TTL re-fetch REFRESHES the existing row in place (narrative,
                 hash, timestamp) - the only writer in the coder that updates a narrative.
                 Tier-0 would otherwise reinforce the row and silently keep year-old text,
                 which defeats the entire point of "up-to-date docs".
  voice never sees it.  Like delegate_task, docs7 stays out of voice.VOICE_TOOL_NAMES: a
                 20 s network stall has no place inside a live call.
Kill switch: coder_docs7 (default OFF - outbound network surface, bake on the VPS, then flip
via the reviewed docs7_flip vps-ops job), under the coder_enabled master. Fail-closed into
clean {"ok": False} dicts - never an exception out of the handler.
"""
from __future__ import annotations

import collections
import json
import re
import threading
import time

DEFAULT_API_URL = "https://context7.com/api"       # upstream constants.ts:14 (env-overridable there)
API_KEY_PREFIX = "ctx7sk"                          # sdk/src/client.ts:26
RETURN_CAP = 6000                                  # chars handed back to the agent (full text -> vault)
QUERY_MAX = 512                                    # upstream: "the API trims long values instead of
                                                   # rejecting" (index.ts:468) - we trim client-side too
_NOT_FOUND_TEXT = (
    "Documentation not found or not finalized for this library. This might have happened because "
    "you used an invalid Context7-compatible library ID. To get a valid Context7-compatible "
    "library ID, use the 'resolve-library-id' with the package name you wish to retrieve "
    "documentation for.")                      # api.ts:236-243, verbatim


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


def _window_allow(tenant: str, limit: int) -> bool:
    """Rolling one-hour per-tenant window over NETWORK calls only (a vault-cache hit is free)."""
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


# ------------------------------------------------------------- redaction before egress

def redact_query(text: str) -> str:
    """The privacy gate extends to the network: whatever leaves the box is stripped of private
    blocks and secret-shaped strings first, then trimmed (upstream warns; Hoola enforces)."""
    from .redact import redact_secrets, strip_private
    t = strip_private(str(text or ""))
    t = redact_secrets(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:QUERY_MAX]


# ------------------------------------------------------------- upstream formatting, ported

def _reputation(trust_score) -> str:
    # utils.ts:7-14 verbatim: >=7 High, >=4 Medium, else Low; undefined/negative -> Unknown
    if trust_score is None or trust_score < 0:
        return "Unknown"
    if trust_score >= 7:
        return "High"
    if trust_score >= 4:
        return "Medium"
    return "Low"


def format_search_result(result: dict) -> str:
    """utils.ts:22-63 port: the LLM-facing shape of one library."""
    parts = [
        f"- Title: {result.get('title', '')}",
        f"- Context7-compatible library ID: {result.get('id', '')}",
        f"- Description: {result.get('description', '')}",
    ]
    snips = result.get("totalSnippets")
    if snips is not None and snips != -1:                     # hidden when -1 / absent
        parts.append(f"- Code Snippets: {snips}")
    parts.append(f"- Source Reputation: {_reputation(result.get('trustScore'))}")
    bench = result.get("benchmarkScore")
    if bench is not None and bench > 0:                       # shown only when positive
        parts.append(f"- Benchmark Score: {bench}")
    versions = result.get("versions")
    if versions:
        parts.append(f"- Versions: {', '.join(str(v) for v in versions)}")
    if result.get("source"):
        parts.append(f"- Source: {result['source']}")
    return "\n".join(parts)


def format_search_results(response: dict) -> str:
    """utils.ts:67-84 port: the teamspace-filter note (when present), then the divider join."""
    results = (response or {}).get("results") or []
    if not results:
        return "No documentation libraries found matching your query."
    parts: list[str] = []
    if (response or {}).get("searchFilterApplied"):
        parts.append(
            "**Note:** Your results only include libraries matching your teamspace's library "
            "filters. To adjust quality thresholds or blocked libraries, update your filters at "
            "https://context7.com/dashboard?tab=policies")
    parts.append("\n----------\n".join(format_search_result(r) for r in results))
    return "\n\n".join(parts)


def _error_text(status: int, body: str, has_key: bool) -> str:
    """parseErrorResponse (api.ts:30-52) port: the API's own message wins, then status semantics."""
    msg = None
    try:
        j = json.loads(body) if body else None
        if isinstance(j, dict):
            msg = j.get("message") or j.get("error")
    except Exception:
        msg = None
    if msg:
        return str(msg)
    if status == 429:
        return ("Rate limited or quota exceeded. Upgrade your plan at https://context7.com/plans "
                "for higher limits." if has_key else
                "Rate limited or quota exceeded. Create a free API key at "
                "https://context7.com/dashboard for higher limits.")
    if status == 404:
        return ("The library you are trying to access does not exist. Please try with a "
                "different library ID.")
    if status == 401:
        return ("Invalid API key. Please check your API key. API keys should start with "
                "'ctx7sk' prefix.")
    return f"Request failed with status {status}. Please try again later."


def _headers() -> dict:
    h = {"X-Context7-Source": "hoola-coder",                # the mcp-server twin (encryption.ts:59)
         "X-Context7-Server-Version": "0.523.0"}           # SERVER_VERSION twin
    key = str(_cfg("context7_api_key", "") or "")
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


async def _http(url: str, headers: dict, params: dict, timeout: float) -> tuple[int, str]:
    """The ONE network seam (tests monkeypatch this). One attempt - drop-don't-wait."""
    import httpx
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
        r = await c.get(url, headers=headers, params=params)
        return r.status_code, r.text


# ------------------------------------------------------------- the vault IS the cache

def _doc_title(library_id: str, query: str) -> str:
    return f"Context7 {library_id}: {query}"


def _vault_row(tenant: str, library_id: str, query: str) -> tuple[str, dict] | None:
    """("fresh", row) within the TTL, ("stale", row) past it, None when the vault has no row.
    Stale matters: the re-fetch will Tier-0-reinforce that row, and docs7 then refreshes it
    in place instead of leaving year-old text under an up-to-date title."""
    from . import store
    store.ensure()
    nk = store.title_norm_key(tenant, _doc_title(library_id, query))
    with store.db() as c:
        row = c.execute(
            "SELECT id, narrative, created_epoch FROM observations "
            "WHERE tenant=? AND title_norm_key=? AND type='docs7' AND superseded_by=0 "
            "ORDER BY id DESC LIMIT 1", (tenant, nk)).fetchone()
    if row is None:
        return None
    ttl_h = int(_cfg("coder_docs7_ttl_hours", 168) or 168)
    age = time.time() - (row["created_epoch"] or 0)
    return ("fresh" if age <= ttl_h * 3600 else "stale"), dict(row)


def _refresh_vault_row(obs_id: int, conv: str, title: str, narrative: str) -> None:
    """The living-row exception: a docs7 row is a mirror of an upstream page, so a post-TTL
    re-fetch updates narrative + hash + timestamp IN PLACE (narrow: type='docs7' only)."""
    from . import store
    store.ensure()
    with store.db(write=True) as c:
        c.execute(
            "UPDATE observations SET narrative=?, content_hash=?, created_at=?, created_epoch=? "
            "WHERE id=? AND type='docs7'",
            (narrative[:8000], store.content_hash(conv, title, narrative),
             time.strftime("%Y-%m-%dT%H:%M:%S%z"), int(time.time()), obs_id))


def _land_in_vault(conv: str, tenant: str, library_id: str, query: str, text: str,
                   language: str | None) -> int | None:
    from . import store
    title = _doc_title(library_id, query)
    facts = [f"library:{library_id}"]
    if language:
        facts.append(f"language:{language}")
    return store.store_observation(
        conv, tenant,
        {"type": "docs7", "title": title, "subtitle": "up-to-date library docs via Context7",
         "narrative": text[:8000], "facts": facts, "concepts": [library_id],
         "files_read": [], "files_modified": []},
        actor="docs7")


# ------------------------------------------------------------- the two ops

async def op_resolve(query: str, library_name: str, tenant: str) -> dict:
    """resolve-library-id (index.ts:340-429): search {base}/v2/libs/search, format like upstream."""
    base = str(_cfg("context7_api_url", DEFAULT_API_URL) or DEFAULT_API_URL).rstrip("/")
    q, name = redact_query(query), redact_query(library_name)
    if not name:
        return {"ok": False,
                "error": "library_name is required for op=resolve (the official name, e.g. 'Next.js')"}
    try:
        status, body = await _http(f"{base}/v2/libs/search", _headers(),
                                   {"query": q, "libraryName": name},
                                   float(_cfg("coder_docs7_timeout_s", 20) or 20))
    except Exception as e:
        return {"ok": False, "error": f"context7 unreachable: {type(e).__name__}: {str(e)[:200]}"}
    has_key = bool(_cfg("context7_api_key", "") or "")
    if status != 200:
        return {"ok": False, "error": _error_text(status, body, has_key), "status": status}
    try:
        data = json.loads(body)
    except Exception:
        return {"ok": False, "error": _error_text(status, body, has_key), "status": status}
    results = data.get("results") or []
    if not results:
        text = data.get("error") or "No libraries found matching the provided name."  # index.ts:410-413
        return {"ok": True, "text": text, "results": []}
    return {"ok": True,
            "text": f"Available Libraries:\n\n{format_search_results(data)}",   # index.ts:423
            "results": results[:10]}


async def op_query(query: str, library_id: str, language: str | None, conv: str,
                   tenant: str) -> dict:
    """query-docs (index.ts:434-486): GET {base}/v2/context; the vault answers within TTL;
    every successful fetch lands in the vault (and refreshes a stale row in place)."""
    base = str(_cfg("context7_api_url", DEFAULT_API_URL) or DEFAULT_API_URL).rstrip("/")
    q = redact_query(query)
    if not library_id or not str(library_id).startswith("/"):
        return {"ok": False,
                "error": ("Pass a Context7 library ID in the /org/project (or /org/project/version) "
                          "form - call docs7 op=resolve first unless the user gave the ID directly.")}
    library_id = str(library_id).strip()

    cached = _vault_row(tenant, library_id, q)
    if cached and cached[0] == "fresh":
        return {"ok": True, "text": (cached[1]["narrative"] or "")[:RETURN_CAP],
                "library_id": library_id, "cached": True, "obs_id": cached[1]["id"]}

    if not _window_allow(tenant, int(_cfg("coder_docs7_max_per_hour", 12) or 12)):
        return {"ok": False,
                "error": ("docs7 courtesy window reached for this hour (coder_docs7_max_per_hour) - "
                          "ask again later or narrow the question.")}
    params: dict = {"query": q, "libraryId": library_id}
    if language:
        params["language"] = str(language)[:64]
    try:
        status, body = await _http(f"{base}/v2/context", _headers(), params,
                                   float(_cfg("coder_docs7_timeout_s", 20) or 20))
    except Exception as e:
        return {"ok": False, "error": f"context7 unreachable: {type(e).__name__}: {str(e)[:200]}"}
    has_key = bool(_cfg("context7_api_key", "") or "")
    if status != 200:
        return {"ok": False, "error": _error_text(status, body, has_key), "status": status}
    if not body.strip():                                   # empty body = a valid not-found (api.ts:231-243)
        return {"ok": True, "text": _NOT_FOUND_TEXT, "library_id": library_id, "outcome": "not_found"}

    obs_id = _land_in_vault(conv, tenant, library_id, q, body, language)
    if cached and cached[0] == "stale" and obs_id == cached[1]["id"]:
        try:                                               # the living-row refresh (see module doc)
            _refresh_vault_row(obs_id, conv, _doc_title(library_id, q), body)
        except Exception:
            pass                                           # the fetch already succeeded; storage is best-effort
    return {"ok": True, "text": body[:RETURN_CAP], "chars": len(body),
            "library_id": library_id, "cached": False, "obs_id": obs_id}


# ------------------------------------------------------------- the ONE tool

DOCS7_SCHEMA = {
    "name": "docs7",
    "description": (
        "Fetch UP-TO-DATE, version-specific documentation and code examples for any programming "
        "library or framework (the Context7 network), instead of trusting training data. Two ops: "
        "op=resolve turns a library NAME into a Context7 ID (/org/project); op=query pulls the "
        "docs for one ID. Call resolve FIRST unless the user already gave an ID in /org/project "
        "or /org/project/version form. Max 3 network calls per question. One CONCEPT per query - "
        "split multi-topic questions into separate query calls. Prefer version-specific IDs when "
        "the user names a version ('Next.js 16' -> /vercel/next.js/v16.x). NEVER put secrets "
        "(keys, passwords, credentials, personal data) in a query - it is redacted before it "
        "leaves the box and stored redacted in her memory."),
    "input_schema": {
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["resolve", "query"],
                   "description": "resolve = name -> library ID; query = fetch docs for an ID"},
            "query": {"type": "string",
                      "description": "What to look up, ONE concept, specific ('React useEffect "
                                     "cleanup function examples'), never 'auth' alone, never "
                                     "multi-topic 'routing and auth and caching'"},
            "library_name": {"type": "string",
                             "description": "op=resolve only: the official library name with "
                                            "proper punctuation ('Next.js', not 'nextjs')"},
            "library_id": {"type": "string",
                           "description": "op=query only: Context7 ID from resolve or the user, "
                                          "e.g. '/vercel/next.js' or '/vercel/next.js/v16.2.9'"},
            "language": {"type": "string",
                         "description": "Optional: the programming language ('Python', "
                                        "'TypeScript') - ranks matching code examples first"},
        },
        "required": ["op", "query"],
    },
}

DOCS7_TOOLS = [DOCS7_SCHEMA]
DOCS7_LABELS = {"docs7": "Library ka taaza documentation laa rahi hoon"}
DOCS7_HANDLERS: dict = {"docs7": None}                     # set below


async def docs7(ctx, op: str = "query", query: str = "", library_name: str = "",
                library_id: str = "", language=None, **_):
    """The one Context7 surface. Gates -> redact -> (vault cache | one network call) -> vault."""
    st = _settings()
    if not getattr(st, "coder_enabled", True):
        return {"ok": False, "error": "coder memory is switched off (coder_enabled)"}
    if not getattr(st, "coder_docs7", False):
        return {"ok": False, "error": "docs7 is switched off (coder_docs7) - bake, then flip"}
    tenant = getattr(ctx, "tenant_id", "-") or "-"
    conv = getattr(ctx, "conversation_id", "") or ""
    op = str(op or "").strip().lower()
    if op == "resolve":
        return await op_resolve(query, library_name, tenant)
    if op == "query":
        return await op_query(query, str(library_id or "").strip(),
                              str(language).strip() if language else None, conv, tenant)
    return {"ok": False, "error": "unknown op - use 'resolve' or 'query'"}


DOCS7_HANDLERS["docs7"] = docs7
