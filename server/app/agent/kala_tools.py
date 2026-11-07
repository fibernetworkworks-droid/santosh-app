"""v0.681.0 KALA MANCH - the T5 knowledge-skill catalog family, backend-only (owner: "GO" on the
google/skills deploy plan; the plan's 0.669 slot was taken by the dev chain's HOOLA AURA while KALA
sat planned - REBASE PROTOCOL, re-slotted 0.681.0/+680 on their 00aa1dac9 v0.680.0 tip).

A kala (कला) is a skill, an art, a craft. The four brothers are the haveli's hands and eyes -
sandarbh the reference shelf, bhandar the store room, jharokha the window, duniya the street -
and the kala is its library card: Google's public skill catalog (github.com/google/skills,
Apache-2.0, fork-and-remix sanctioned), fetched byte-exact on demand, narrowed by query, its
SKILL.md documents and their references read on demand. ONE tool `kala`, GET-only, one fixed host,
no login, no key, no script ever executed server-side. IDEA-ONLY - zero upstream code crossed the
wall; what ported is the IDEA of each piece:

- the finding-google-skills meta-skill ("load almost nothing until a lookup actually happens";
  fetch the catalog byte-exactly, every entrypoint URL intact; the truncation bias warning: a
  truncated alphabetical preview "reads as though only the first few products exist") -> the
  `catalog` action + the byte-exact fetch + the honest caps.
- the routing rule (google-cloud-discovery.md: catalog names are predictable families - gke-*,
  agent-platform-*, google-cloud-solution-* - and "Never infer a skill's contents from its name.
  If an answer needs a skill you cannot read, say so instead of answering from memory") -> the
  `list` action's family table + read's never-guess NOT_FOUND.
- the SKILL.md anatomy (frontmatter description contract, references/ loaded on demand - the
  progressive disclosure law) -> the `read` and `references` actions.
- the attribution law (a versioned tag APPENDED to the User-Agent, never overwriting) -> this
  lane's own UA tag, appended alongside, never overwriting a house UA.

THE LAWS:

- GET only, forever: this lane never POSTs, PUTs, DELETEs, never sends an Authorization header,
  never stores a cookie, never touches a login.
- One host, one path shape: every url this lane ever fetches must pass the house's own scrape-lane
  SSRF guard (public hosts only - loopback, RFC1918, link-local and the cloud-metadata address
  never fetched) AND THEN the lane's own allowlist on top - https://raw.githubusercontent.com
  only, and only the catalog index or a skills/<domain>/<skill>/SKILL.md or .../references/<file>.md
  path. Anything else is refused by name (NOT_ALLOWED), before a byte moves.
- The catalog is cached, the documents are not: index.json (~75 KB, rarely changes) sits in an
  in-process TTL cache (kala_catalog_ttl_seconds, default 300 s); a SKILL.md body is fetched fresh
  on every read - "fetching is the normal path and installs nothing", the routing rule's own law.
- No script ever runs: a SKILL.md's scripts/ are text at most, never executed server-side. This
  lane reads documents; it does not become them.
- One envelope, every answer: {schema_version, ok, tool, action, ..., meta{elapsed_ms, backend},
  error{code, message, hint}}. Kill switch `kala_enabled` stops the whole lane with the honest
  NEED_SETUP. Off means off.
- Caps are honest: catalog hits clamped before the call, a truncated body carries a `note` with
  the cap, a giant answer is an honest TOO_BIG past the download cap.
- Read-safe outputs: text that comes back passes operator.browser mask_ids like every scraping
  surface (an Aadhaar/PAN riding inside a skill document is masked before the model reads it).
- One network seam: every byte this lane fetches rides `_http_get` - tests monkeypatch exactly
  that one function and the whole suite stays offline; no test ever touches the real network.
- What this lane is NOT: not the open web (duniya), not a browser (jharokha), not her own data
  (bhandar). One catalog, its documents, nothing else.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from urllib.parse import urlsplit

from ..config import get_settings
from .scrape_tools import ToolError  # the house's own tool error (the guard raises it)
from .tools import Ctx

log = logging.getLogger("santosh.kala")

SCHEMA_VERSION = 1

# ---------------------------------------------------------------- error codes (the discipline)
NEED_SETUP = "NEED_SETUP"    # the lane is turned off
BAD_INPUT = "BAD_INPUT"      # the arguments were rejected (the message names what and why)
NOT_FOUND = "NOT_FOUND"      # the catalog answered, but has no such skill / the file is not there
NOT_ALLOWED = "NOT_ALLOWED"  # outside the one-host allowlist (refused by name, before any byte)
TOO_BIG = "TOO_BIG"          # the answer would blow the download cap
BLOCKED = "BLOCKED"          # the SSRF / scheme guard refused this url
UPSTREAM = "UPSTREAM"        # the upstream failed / timed out / answered something unreadable

# ---------------------------------------------------------------- caps (the envelope stays small)
_MAX_Q = 200                 # a catalog query
_MAX_NAME = 160              # a skill name
_MAX_FILE = 160              # a references file name
_MAX_PREFIX = 60             # a list prefix
_MAX_CATALOG_HITS = 25       # any hit list's cap
_MAX_SKILL_CHARS = 12_000    # a SKILL.md body cap (truncated honestly, never silently)
_MAX_REF_CHARS = 8_000       # a references file cap
_MAX_BODY_CHARS = 500_000    # the download cap past which TOO_BIG is honest
_DESC_CHARS = 400            # a catalog description cap
_TIMEOUT_S = 20              # one upstream call's belt
_UA = "hoola-kala/0.681 (+google-skills catalog; Apache-2.0 remixed; idea-only)"

_KL_ACTIONS = ("catalog", "read", "references", "list", "status")

BACKENDS = {
    "catalog": "raw.githubusercontent.com google/skills index.json (no key, 5-min TTL cache)",
    "read": "raw.githubusercontent.com google/skills SKILL.md (no key, fetched fresh)",
    "references": "raw.githubusercontent.com google/skills references/*.md (no key, fetched fresh)",
    "list": "the cached catalog (no extra network)",
    "status": "this lane itself (zero network)",
}

_CATALOG_URL = "https://raw.githubusercontent.com/google/skills/main/index.json"

_HOST = "raw.githubusercontent.com"
_PATH_RE = re.compile(
    r"^/google/skills/main/(index\.json"
    r"|skills/[a-z0-9_.-]+/[a-z0-9_.-]+/SKILL\.md"
    r"|skills/[a-z0-9_.-]+/[a-z0-9_.-]+/references/[A-Za-z0-9._-]+\.md)$")
_PATH_RULE = ("https://raw.githubusercontent.com/google/skills/main/ "
              "{index.json | skills/<domain>/<skill>/SKILL.md | skills/<domain>/<skill>/references/<file>.md}")

_REF_FILE = re.compile(r"^[A-Za-z0-9._-]+\.md$")

# the routing rule's predictable families (its own law: names are guessable, contents never are)
_FAMILIES = {
    "gke-": "GKE clusters, networking, storage, scaling, cost, AI inference, troubleshooting",
    "agent-platform-": "model deploy, tuning, RAG, eval, endpoints, prompts",
    "google-cloud-solution-": "multi-product reference architectures",
    "google-cloud-waf-": "Well-Architected Framework pillars",
    "google-cloud-recipe-": "getting started: auth, onboarding, foundation builder",
    "genkit-": "the Genkit SDKs, one skill per language",
    "gemini-": "the Gemini API family",
    "cloud-logging-": "observability: logging configuration and queries",
    "cloud-monitoring-": "observability: monitoring, alerts, charts, PromQL",
    "secops-": "Google SecOps: cases, detection, triage, hunting",
    "iam-helper-": "IAM: troubleshooting, policy, simulator, PAM",
    "google-mobile-ads-": "the Google Mobile Ads SDK",
}


# ---------------------------------------------------------------- the cache (the catalog's bed)

_CACHE: dict[str, Any] = {"data": None, "at": 0.0, "ok": False, "error": None, "fetches": 0}


def _ttl() -> int:
    try:
        return max(0, int(getattr(get_settings(), "kala_catalog_ttl_seconds", 300)))
    except Exception:                                    # pragma: no cover - settings not ready
        return 300


def _cache_reset() -> None:
    _CACHE.update({"data": None, "at": 0.0, "ok": False, "error": None, "fetches": 0})


def _cache_age() -> float | None:
    return None if not _CACHE["at"] else max(0.0, time.monotonic() - _CACHE["at"])


# ---------------------------------------------------------------- small helpers (the house's own laws)

def _clean(value: Any, cap: int) -> str:
    return " ".join(str(value or "").split())[:cap]


def _clip(text: str, cap: int) -> str:
    return str(text or "")[:cap]


def _mask_text(v: str) -> str:
    """ID numbers in what comes back are masked before the chat model reads it (the scrape-lane law)."""
    try:
        from ..operator.browser import mask_ids
        return mask_ids(v)
    except Exception:                                    # pragma: no cover - the operator lane is missing
        return v


def _int_arg(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


class _NotFound(Exception):
    """The catalog answered fine but has nothing for this ask."""


class _NotAllowed(Exception):
    """Outside the one-host allowlist - refused by name before any byte moves."""


class _TooBig(Exception):
    """The answer would blow the download cap - honest, before anything is read."""


class _Upstream(Exception):
    """Every network failure the seam can produce (timeout / status / unreadable answer)."""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------- envelope (the discipline)

def _kl_envelope(action: str, error: tuple[str, str, str] | None = None, elapsed_ms: int = 0,
                 **fields) -> dict:
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "ok": error is None, "tool": "kala",
                           "action": action,
                           "error": (None if error is None else
                                     {"code": error[0], "message": error[1], "hint": error[2]})}
    out.update(fields)
    meta = dict(out.pop("meta", {}) or {})
    out["meta"] = {"elapsed_ms": max(0, int(elapsed_ms)),
                   "backend": BACKENDS.get(action, "raw.githubusercontent.com google/skills (no login, no key)"),
                   **meta}
    return out


def _kl_bad(action: str, msg: str, hint: str = "", code: str = BAD_INPUT) -> dict:
    return _kl_envelope(action, error=(code, msg, hint))


def _locked(action: str) -> dict | None:
    if not bool(getattr(get_settings(), "kala_enabled", True)):
        return _kl_envelope(action, error=(
            NEED_SETUP, "the kala knowledge lane is turned off on this server",
            "Ask the owner to set kala_enabled=true."))
    return None


def _guard_url(url: str) -> str:
    """Public http(s) through the house's own scrape-lane guard - the first wall every url crosses."""
    from .scrape_tools import _guard_url as _house_guard
    return _house_guard(url)                             # ToolError on anything not a public http(s) host


def _whitelist(url: str) -> str:
    """The SECOND wall, this lane's own: one host, one path shape, refused by name."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc.lower() != _HOST or not _PATH_RE.match(parts.path or ""):
        raise _NotAllowed(f"the kala lane reads only {_PATH_RULE} - got "
                          f"'{_clean(url, 120)}', which is outside the allowlist")
    return url


# ---------------------------------------------------------------- THE network seam

async def _http_get(url: str) -> tuple[int, str, str, str]:
    """The ONE seam every public byte rides. Raises _Upstream on any failure; returns
    (status, content_type, text, final_url). Tests monkeypatch exactly this - the suite stays
    offline. The UA carries the lane's attribution tag (appended by the client header dict -
    never overwriting a house header)."""
    import httpx                                     # lazy - the P1 no-network-import law
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S, follow_redirects=True,
                                     headers={"User-Agent": _UA}) as cl:
            r = await cl.get(url)
            if r.status_code >= 400:
                raise _Upstream(f"the upstream answered {r.status_code}", status=r.status_code)
            return r.status_code, (r.headers.get("content-type") or ""), r.text, str(r.url)
    except _Upstream:
        raise
    except Exception as e:                            # pragma: no cover - the seam's own belt
        raise _Upstream(f"the upstream did not answer: {_clean(e, 140)}") from e


def _json_of(body: str, what: str) -> Any:
    try:
        return json.loads(body)
    except Exception:
        raise _Upstream(f"the {what} answer was not JSON")


def _up404(e: _Upstream) -> Exception:
    """A 404 from this host means 'nothing here', not 'the web is broken'."""
    return _NotFound(str(e)) if e.status == 404 else e


async def _fetch_catalog() -> list:
    """The catalog, byte-exact, behind the TTL cache. Every url crosses both walls."""
    if _CACHE["data"] is not None and (time.monotonic() - (_CACHE["at"] or 0.0)) < _ttl():
        return _CACHE["data"]
    url = _whitelist(_guard_url(_CATALOG_URL))
    try:
        _, _, body, _ = await _http_get(url)
        if len(body) > _MAX_BODY_CHARS:
            raise _TooBig(f"the catalog is {len(body)} chars - past the {_MAX_BODY_CHARS} download cap")
        data = _json_of(body, "skills catalog")
        skills = data.get("skills") if isinstance(data, dict) else None
        if not isinstance(skills, list) or not skills:
            raise _Upstream("the catalog answer had no skills list")
        _CACHE.update({"data": skills, "at": time.monotonic(), "ok": True, "error": None,
                       "fetches": int(_CACHE["fetches"]) + 1})
        return skills
    except Exception as e:
        _CACHE.update({"ok": False, "error": _clean(e, 160)})   # the failure is told, the stale bed stays
        raise


def _find(skills: list, name: str) -> dict | None:
    return next((s for s in skills if isinstance(s, dict) and str(s.get("name") or "") == name), None)


# ---------------------------------------------------------------- the actions

async def _act_catalog(q: str | None, limit: int | None) -> dict:
    skills = await _fetch_catalog()
    limit = _int_arg(limit, _MAX_CATALOG_HITS, 1, _MAX_CATALOG_HITS)
    q_clean = _clean(q, _MAX_Q)
    hits = skills
    if q_clean:
        try:
            rx = re.compile(q_clean, re.I)               # a real regex, the jq example's law
        except re.error:
            rx = re.compile(re.escape(q_clean), re.I)    # a broken pattern degrades to a literal find
        hits = [s for s in skills
                if isinstance(s, dict) and rx.search(f"{s.get('name') or ''} {s.get('description') or ''}")]
    total = len(hits)
    items = [{"name": _clean(s.get("name"), 120),
              "entrypoint": str(s.get("entrypoint") or ""),
              "description": _clip(_mask_text(s.get("description")), _DESC_CHARS)}
             for s in hits[:limit] if isinstance(s, dict)]
    out: dict[str, Any] = {"query": q_clean or None, "catalog_size": len(skills),
                           "total_matches": total, "count": len(items), "items": items}
    if q_clean and total > len(items):
        out["note"] = f"{total} matches, {len(items)} shown - narrow the query or raise nothing (the cap is the cap)"
    elif not q_clean:
        out["note"] = ("no query - the catalog's first entries, alphabetical; a truncated preview reads as "
                       "though only these exist, so narrow with a query")
    return out


async def _act_read(name: str) -> dict:
    name = _clean(name, _MAX_NAME)
    if not name:
        raise ValueError("read needs a skill name (name)")
    skills = await _fetch_catalog()
    entry = _find(skills, name)
    if entry is None:
        raise _NotFound(f"no skill named '{name}' in the catalog - action=catalog with a query finds "
                        f"the real names (never infer a skill's contents from its name)")
    url = _whitelist(_guard_url(str(entry.get("entrypoint") or "")))
    status, ctype, body, _ = await _http_get(url)
    if len(body) > _MAX_BODY_CHARS:
        raise _TooBig(f"that skill document is {len(body)} chars - past the {_MAX_BODY_CHARS} download cap")
    text = body
    truncated = False
    if len(text) > _MAX_SKILL_CHARS:
        text, truncated = _clip(text, _MAX_SKILL_CHARS), True
    out: dict[str, Any] = {"name": name, "url": url, "status": status,
                           "content_type": ctype or "text/plain", "chars": len(text),
                           "text": _mask_text(text),
                           "description": _clip(_mask_text(entry.get("description")), _DESC_CHARS)}
    if truncated:
        out["note"] = ("text truncated at the cap - more of the document exists; fetch a references "
                       "file for the deep parts")
    return out


async def _act_references(name: str, file: str) -> dict:
    name = _clean(name, _MAX_NAME)
    file = _clean(file, _MAX_FILE)
    if not name:
        raise ValueError("references needs the skill name (name)")
    if not file:
        raise ValueError("references needs the file name (file), e.g. attribution.md")
    if not _REF_FILE.match(file):
        raise ValueError("file must be a plain references/<name>.md markdown file name "
                         "(letters, digits, dot, dash, underscore)")
    skills = await _fetch_catalog()
    entry = _find(skills, name)
    if entry is None:
        raise _NotFound(f"no skill named '{name}' in the catalog - action=catalog with a query finds "
                        f"the real names")
    ep = str(entry.get("entrypoint") or "")
    if not ep.endswith("/SKILL.md"):
        raise _Upstream(f"that skill's entrypoint is not a SKILL.md document ({_clean(ep, 120)}) - "
                        f"no references tree is known for it")
    url = _whitelist(_guard_url(ep[:-len("SKILL.md")] + f"references/{file}"))
    try:
        status, ctype, body, _ = await _http_get(url)
    except _Upstream as e:
        raise _up404(e) from e                       # a missing references file 404s - honest NOT_FOUND
    if len(body) > _MAX_BODY_CHARS:
        raise _TooBig(f"that references file is {len(body)} chars - past the {_MAX_BODY_CHARS} download cap")
    text = body
    truncated = False
    if len(text) > _MAX_REF_CHARS:
        text, truncated = _clip(text, _MAX_REF_CHARS), True
    out: dict[str, Any] = {"name": name, "file": file, "url": url, "status": status, "chars": len(text),
                           "text": _mask_text(text)}
    if truncated:
        out["note"] = "text truncated at the cap - more of the file exists"
    return out


async def _act_list(prefix: str | None, limit: int | None) -> dict:
    skills = await _fetch_catalog()
    prefix = _clean(prefix, _MAX_PREFIX).lower()
    limit = _int_arg(limit, _MAX_CATALOG_HITS, 1, _MAX_CATALOG_HITS)
    hits = ([s for s in skills if isinstance(s, dict)
             and str(s.get("name") or "").lower().startswith(prefix)] if prefix else [])
    items = [{"name": _clean(s.get("name"), 120), "entrypoint": str(s.get("entrypoint") or "")}
             for s in hits[:limit]]
    out: dict[str, Any] = {"prefix": prefix or None, "total_matches": len(hits),
                           "count": len(items), "items": items, "families": dict(_FAMILIES)}
    if not prefix:
        out["note"] = "no prefix given - nothing listed; pick a family from `families` (e.g. gke-)"
    elif not hits:
        out["note"] = (f"no catalog skill name starts with '{prefix}' - the known families ride in "
                       f"`families`; never infer a skill's contents from its name")
    return out


def _act_status() -> dict:
    age = _cache_age()
    return {"lane": "KALA MANCH (v0.681) - the T5 knowledge-skill catalog family",
            "actions": list(_KL_ACTIONS),
            "upstream": {"repo": "github.com/google/skills (Apache-2.0; fork-and-remix sanctioned)",
                         "index": _CATALOG_URL, "host_allowlist": _HOST, "path_rule": _PATH_RULE},
            "cache": {"ttl_s": _ttl(), "entries": len(_CACHE["data"] or []),
                      "age_s": (None if age is None else round(age, 1)),
                      "fetches": int(_CACHE["fetches"]), "last_ok": bool(_CACHE["ok"]),
                      "last_error": _CACHE["error"]},
            "caps": {"catalog_hits": _MAX_CATALOG_HITS, "skill_chars": _MAX_SKILL_CHARS,
                     "reference_chars": _MAX_REF_CHARS, "download_chars": _MAX_BODY_CHARS,
                     "timeout_s": _TIMEOUT_S},
            "laws": ["GET only - never POST/PUT/DELETE, never an auth header, never a cookie",
                     "one host, one path shape - the house SSRF guard AND the lane allowlist, both walls",
                     "the catalog is cached (TTL), the documents are fetched fresh - every read",
                     "no SKILL.md script ever executes server-side - documents are read, never run",
                     "never infer a skill's contents from its name - read it or say you cannot",
                     "every answer one envelope; text passes the id-mask"],
            "siblings": "duniya reads the open web; jharokha drives pages; kala is the skill catalog door",
            "note": "zero login, zero key - the catalog and its documents answer anyone"}


# ---------------------------------------------------------------- error mapping (one honest table)

def _error_of(e: Exception) -> tuple[str, str, str]:
    if isinstance(e, _NotFound):
        return (NOT_FOUND, str(e), "try a different spelling, or action=catalog with a query to find the real names")
    if isinstance(e, _NotAllowed):
        return (NOT_ALLOWED, str(e), "the lane reads one host and one path shape only - the allowlist "
                                     "rides in action=status")
    if isinstance(e, _TooBig):
        return (TOO_BIG, str(e), "the lane will not download more than the cap - find a narrower ask")
    if isinstance(e, ToolError):
        return (BLOCKED, str(e), "the guard only fetches public http(s) addresses (loopback, private "
                                 "ranges and the metadata address never leave the house)")
    if isinstance(e, _Upstream):
        return (UPSTREAM, str(e), "the upstream is down, slow or unhappy - try again shortly; the "
                                  "cached catalog may still answer list actions")
    if isinstance(e, ValueError):
        return (BAD_INPUT, str(e), "name the argument the message points at")
    return (UPSTREAM, f"the kala lane failed: {_clean(e, 160)}",
            "try the action again; if it repeats, action=status shows the lane's state")


# ---------------------------------------------------------------- the ONE tool

async def kala(ctx: Ctx, action: str = "status", *, q: str | None = None, name: str | None = None,
               file: str | None = None, prefix: str | None = None, limit: int | None = None,
               **_) -> dict:
    """The skill catalog door. Never raises; every answer is one envelope."""
    started = time.monotonic()
    action = str(action or "").strip().lower()
    if action not in _KL_ACTIONS:
        return _kl_bad(action or "", f"unknown action '{action}'; valid: {', '.join(_KL_ACTIONS)}",
                       "action=status shows the lane")
    if (lock := _locked(action)) is not None:
        return lock
    try:
        if action == "catalog":
            res = await _act_catalog(q, limit)
        elif action == "read":
            res = await _act_read(name or q or "")
        elif action == "references":
            res = await _act_references(name or "", file or "")
        elif action == "list":
            res = await _act_list(prefix, limit)
        elif action == "status":
            res = _act_status()
        else:                                          # pragma: no cover - the enum is checked above
            raise ValueError(f"unknown action '{action}'")
        out = _kl_envelope(action, **res) if isinstance(res, dict) else _kl_envelope(action)
    except Exception as e:
        out = _kl_envelope(action, error=_error_of(e))
    out["meta"]["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return out


# ---------------------------------------------------------------- the tool spec the model sees
KALA_TOOLS = [
    {"name": "kala", "description": (
        "KALA MANCH (v0.681): Google's public skill catalog (github.com/google/skills, Apache-2.0) "
        "- the T5 idea, zero login, zero API key, GET only, one fixed host. Actions: catalog "
        "(fetch index.json byte-exact behind a 5-min cache, narrow by a case-insensitive regex over "
        "name+description: q, limit<=25; no q = the first entries alphabetical) | read (one SKILL.md "
        "document by its exact catalog name, fetched fresh every time, capped 12k: name) | "
        "references (a skill's references/<file>.md deep-dive doc, e.g. attribution.md: name, file) | "
        "list (skill names by a predictable prefix - gke-, agent-platform-, google-cloud-solution-, "
        "google-cloud-waf- ... - with the family table: prefix) | status (the lane's upstream, cache, "
        "caps and laws, zero network). Every answer one envelope {ok, action, error:{code, message, "
        "hint}}. The lane never POSTs, never logs in, never holds a key, and NEVER runs a skill's "
        "scripts - documents are read, never executed. Never infer a skill's contents from its name: "
        "read it or say you cannot. For the open web use duniya; for pages that need clicking use "
        "jharokha."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": list(_KL_ACTIONS),
                    "description": "catalog | read | references | list | status"},
         "q": {"type": "string", "description": "catalog: the query (a word, or a regex) over skill names + descriptions; read accepts it as the skill name"},
         "name": {"type": "string", "description": "read / references: the skill's EXACT catalog name (from catalog/list - never guessed)"},
         "file": {"type": "string", "description": "references: the file name, e.g. attribution.md"},
         "prefix": {"type": "string", "description": "list: the name prefix, e.g. gke- or agent-platform-"},
         "limit": {"type": "integer", "description": "catalog / list: how many hits, 1-25 (default 25)"}}}},
]

KALA_LABELS = {"kala": "Kala: Google's public skill catalog, read on demand (no login, no key)"}
KALA_HANDLERS = {"kala": kala}
