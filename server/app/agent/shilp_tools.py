"""v0.730.0 SHILP MANCH - the ArtCraft generation lane, backend-only (owner: "MAKE A PLAN FOR
HOOLA AI THUS HOOLA USER CAN USE THIS" on the storytold/artcraft recon; shilp = craft).

ArtCraft (github.com/storytold/artcraft, MIT/Apache-2.0) is "the IDE for artists": interactive
AI image and video creation across a 62-model catalog (images, video, music and sound, 3D
meshes, worlds). Its **Omni API** (documented in their `_docs/artcraft_omni_api.md`, base
https://api.storyteller.ai - their doc's own emphasis: NOT api.getartcraft.com) is the
API-key-authenticated generation surface. This lane puts exactly that documented surface behind
Hoola's doors: she says "make me a video of X", Hoola starts the job, polls it, and hands her
the finished cdn_url. NOTHING is invented: only the four endpoint families their doc proves -
POST /v1/omni_api/generate/video, POST /v1/omni_api/generate/image, GET
/v1/omni_api/job_status/job/{token}, GET /v1/omni_api/job_status/batch - ride this lane;
music/mesh/splat generation endpoints exist in their app but are NOT in the public doc, so they
are NOT here (the kala law: never infer an endpoint from a name; the models action says so
honestly).

THE LAWS:

- BYOK, owner-level: the ArtCraft API key lives in the VPS .env (ARTCRAFT_API_KEY -> config
  artcraft_api_key) and nowhere else - never in chat, never in the repo, never in any envelope.
  API access itself is gated per account by ArtCraft staff (app.getartcraft.com -> Account ->
  Settings -> API Keys). No key = every network action answers honest NEED_SETUP with those
  exact directions; status and models answer keyless.
- Money is hers: every generate call spends the account's ArtCraft credits (their 402). The
  tool fires only on the user's explicit ask in the turn; a 402 maps to the PAYMENT code and is
  FINAL - the lane never retries a payment refusal.
- Idempotency is minted here: a fresh UUID4 per generate call (their doc: "a fresh UUID per
  request; prevents accidental duplicates"), returned in the envelope so a retry is a reasoned
  act, never an accident. Caller-provided tokens are ignored (a stale one would only buy a
  duplicate rejection).
- Reference URLs are data leaving the box: every *_url crosses the lane's own wall BEFORE any
  byte moves - http(s) scheme only (their own rule), no embedded credentials, no loopback /
  private / link-local / reserved / metadata hosts (an internal endpoint must never land in
  their server logs). Shape problems are BAD_INPUT; wall refusals are NOT_ALLOWED.
- URL inputs only: their doc documents the URL-input lane (their server downloads each url
  itself, up to 10 redirects, type-sniffs the bytes). Media-token inputs ride the desktop app -
  the upload endpoints behind them are not in the public doc, so a *_media_tokens field here is
  an honest BAD_INPUT quoting their own mutual-exclusivity rule.
- One network seam: every request rides `_http` - tests monkeypatch exactly that one async
  function and the whole suite stays offline; no test ever touches the real network. No
  top-level httpx import (the P1 inertness law).
- One envelope, every answer: {schema_version, ok, tool, action, ..., meta{elapsed_ms, backend},
  error{code, message, hint}}. Kill switch `shilp_enabled` stops the whole lane with the honest
  NEED_SETUP. Off means off. ALL strings English (the standing rule).
- Jobs are honest: their statuses ride raw (pending / started / attempt_failed still run;
  terminal: complete_success / complete_failure / dead / cancelled_by_user /
  cancelled_by_system). The envelope's `ok` says the CALL succeeded; `job_ok` says the JOB did -
  a failed generation is not a failed lane call and never hides behind one.
- Caps refuse, never clamp: a generation is money; silently trimming a reference list or a
  prompt would change the job behind her back. Past a cap = BAD_INPUT naming the cap.
- What this lane is NOT: not their desktop IDE (compositing, posing, worlds), not a model
  aggregator, not her own media store. One documented API, its jobs, nothing else.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

from ..config import get_settings
from .tools import Ctx

log = logging.getLogger("santosh.shilp")

SCHEMA_VERSION = 1

# ---------------------------------------------------------------- error codes (the discipline)
NEED_SETUP = "NEED_SETUP"    # lane off, or the ArtCraft API key is not set on this server
BAD_INPUT = "BAD_INPUT"      # the arguments were rejected (the message names what and why)
NOT_ALLOWED = "NOT_ALLOWED"  # a reference url hit the lane's wall (private host, credentials)
AUTH = "AUTH"                # their 401: the key is invalid or the account is banned
PAYMENT = "PAYMENT"          # their 402: insufficient credits - FINAL, never retried
UPSTREAM = "UPSTREAM"        # their server failed / timed out / answered something unreadable

# ---------------------------------------------------------------- caps (honest refusals, never clamps)
_MAX_PROMPT = 8_000          # a prompt cap (their side may cap smaller - their 400 is passed through)
_MAX_MODEL = 64              # a model id cap
_MAX_REFS = 20               # any one reference-url field's cap
_MAX_REF_URL = 2_048         # one url's length cap
_MAX_TOKENS = 25             # the batch-status cap (keeps one envelope small)
_TIMEOUT_S = 240             # generation calls are slow - their own python example uses timeout=240

_SH_ACTIONS = ("status", "models", "video", "image", "job", "jobs")

BACKENDS = {
    "status": "this lane itself (zero network)",
    "models": "the curated catalog below (zero network - their public README, dated)",
    "video": "ArtCraft Omni API POST /v1/omni_api/generate/video (BYOK, spends credits)",
    "image": "ArtCraft Omni API POST /v1/omni_api/generate/image (BYOK, spends credits)",
    "job": "ArtCraft Omni API GET /v1/omni_api/job_status/job/{token} (BYOK)",
    "jobs": "ArtCraft Omni API GET /v1/omni_api/job_status/batch (BYOK)",
}

_BASE_DEFAULT = "https://api.storyteller.ai"   # their doc's own emphasis: NOT api.getartcraft.com
_UA = "hoola-shilp/0.730 (+ArtCraft Omni API; BYOK; idea-integration)"

_MODEL_RE = re.compile(r"^[a-z0-9_]{2,64}$")
_JOB_RE = re.compile(r"^jinf_[a-z0-9]{8,48}$")

_TERMINAL_OK = "complete_success"
_TERMINAL_BAD = ("complete_failure", "dead", "cancelled_by_user", "cancelled_by_system")

_TOKENS_RULE = ("Either reference_image_media_tokens or reference_image_urls must be set, "
                "not both")   # their own mutual-exclusivity error, quoted where we refuse early

_TOKEN_FIELDS = ("start_frame_image_media_token", "end_frame_image_media_token",
                 "reference_image_media_tokens", "reference_video_media_tokens",
                 "reference_audio_media_tokens", "image_media_tokens")

# ---------------------------------------------------------------- the curated catalog (their public
# README, dated 2026-11-09; API ids are snake_case - e.g. seedance_2p0, the id their own doc
# example uses - and the API may know more than this list; an unknown id comes back as their
# own 400, passed through. Their markers ride as written: disabled / restricted.)
_MODELS: dict[str, dict[str, list[str]]] = {
    "image": {
        "Nano Banana": ["Nano Banana", "Nano Banana 2", "Nano Banana Pro"],
        "GPT Image": ["GPT Image 1.5", "GPT Image 2", "GPT Image 2.5 Flare", "GPT Image 2.5 Sunburst"],
        "FLUX": ["FLUX.1 [dev]", "FLUX.1 [schnell]", "FLUX 1.1 [pro]", "FLUX 1.1 [pro] ultra"],
        "Seedream": ["Seedream 4", "Seedream 4.5", "Seedream 5 Lite", "Seedream 5.0 Pro",
                     "Seedream 5.0 Pro Ultra"],
    },
    "video": {
        "Seedance": ["Seedance 1.0 Lite (disabled)", "Seedance 1.5 Pro", "Seedance 2.0"],
        "Kling": ["Kling 1.6 Pro", "Kling 2.1 Pro (disabled)", "Kling 2.1 Master (disabled)",
                  "Kling 2.5 Turbo Pro", "Kling 2.6 Pro", "Kling 3.0 Pro (disabled)",
                  "Kling 3.0 Standard (disabled)"],
        "Veo": ["Veo 2 (disabled)", "Veo 3 (disabled)", "Veo 3 Fast", "Veo 3.1", "Veo 3.1 Fast",
                "Veo 3.1 Lite"],
        "Sora": ["Sora 2 (disabled)", "Sora 2 Pro (disabled)"],
        "Vidu": ["Vidu Q3", "Vidu Q3 Turbo"],
        "MiniMax": ["MiniMax H3", "MiniMax H3 Turbo (restricted)", "MiniMax H3 Ultra (restricted)"],
        "Flux": ["Flux 3", "Flux 3 Draft"],
    },
    "audio": {
        "Suno": ["Suno Music", "Suno Remix", "Suno Sounds", "Suno Sample"],
        "Seed Audio": ["Seed Audio 1.0"],
    },
    "mesh": {
        "Hunyuan 3D": ["Hunyuan 3D 2.0", "Hunyuan 3D 2.1", "Hunyuan 3D 3", "Hunyuan 3D 3 Sketch",
                       "Hunyuan 3D 3.1 Pro", "Hunyuan 3D 3.1 Rapid", "Hunyuan 3D 3.1 Part",
                       "Hunyuan 3D 3.1 Smart Topology"],
        "Tripo3D": ["Tripo3D H3.1"],
        "Meshy": ["Meshy 6"],
        "Rodin": ["Rodin 2.5 Fast"],
    },
    "splat": {
        "Marble": ["Marble 1.0", "Marble 1.0 Draft", "Marble 1.1", "Marble 1.1 Plus"],
        "TripoSplat": ["TripoSplat"],
    },
}
_MODELS_NOTE = ("curated from their public README (2026-11-09); Omni API model ids are "
                "snake_case (their doc's example: seedance_2p0) and the API may know more ids "
                "than this display-name list - an unknown id comes back as their own 400; "
                "audio/mesh/splat models have NO documented Omni API endpoint yet, so this lane "
                "generates video and image only")


# ---------------------------------------------------------------- small helpers (the house's own laws)

def _clean(value: Any, cap: int) -> str:
    return " ".join(str(value or "").split())[:cap]


def _clip(text: str, cap: int) -> str:
    return str(text or "")[:cap]


def _base() -> str:
    try:
        b = str(getattr(get_settings(), "artcraft_base_url", "") or "").strip().rstrip("/")
    except Exception:                                    # pragma: no cover - settings not ready
        b = ""
    return b or _BASE_DEFAULT


def _key() -> str:
    try:
        return str(getattr(get_settings(), "artcraft_api_key", "") or "").strip()
    except Exception:                                    # pragma: no cover - settings not ready
        return ""


def _enabled() -> bool:
    try:
        return bool(getattr(get_settings(), "shilp_enabled", True))
    except Exception:                                    # pragma: no cover - settings not ready
        return True


def _headers(api_key: str) -> dict[str, str]:
    """The auth shape their doc prescribes - Bearer recommended, never a cookie."""
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
            "User-Agent": _UA}


class _Refused(Exception):
    """A reference url hit the lane's own wall - refused by name before any byte moves."""


class _Upstream(Exception):
    """Every network failure the seam can produce (timeout / status / unreadable answer)."""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


class _NoKey(Exception):
    """The ArtCraft API key is not set on this server."""


# ---------------------------------------------------------------- the walls (before any byte moves)

_BANNED_NAMES = ("localhost", "metadata.google.internal", "metadata.goog")


def _ref_url(value: Any, field: str) -> str:
    """One reference url through the lane's wall. Shape problems -> ValueError (BAD_INPUT);
    wall refusals -> _Refused (NOT_ALLOWED). Nothing is fetched here - the wall is about what
    we are willing to HAND to their server."""
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(f"{field}: an empty url is not a reference")
    if len(raw) > _MAX_REF_URL:
        raise ValueError(f"{field}: url is {len(raw)} chars - past the {_MAX_REF_URL} cap")
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"{field}: url must start with http:// or https:// (their own rule) - "
                         f"got '{_clip(raw, 120)}'")
    if parts.username or parts.password:
        raise _Refused(f"{field}: urls with embedded credentials are refused - credentials never "
                       f"leave the box, even inside a reference url")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError(f"{field}: url has no host - got '{_clip(raw, 120)}'")
    banned = host in _BANNED_NAMES or host.endswith((".local", ".internal"))
    if not banned:
        try:
            ip = ip_address(host)
            banned = (ip.is_loopback or ip.is_private or ip.is_link_local
                      or ip.is_reserved or ip.is_unspecified)
        except ValueError:
            banned = False                                # a public name - their server resolves it
    if banned:
        raise _Refused(f"{field}: '{host}' is a loopback / private / metadata address - reference "
                       f"urls are data leaving the box, internal endpoints are never handed to "
                       f"their servers")
    return raw


def _ref_urls(values: Any, field: str) -> list[str]:
    """A reference-url LIST through the wall, capped honestly (refuse, never clamp)."""
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{field}: expected a list of urls, got {type(values).__name__}")
    vals = [v for v in values if str(v or "").strip()]
    if len(vals) > _MAX_REFS:
        raise ValueError(f"{field}: {len(vals)} urls - past the {_MAX_REFS} cap (narrow the list)")
    return [_ref_url(v, f"{field}[{i}]") for i, v in enumerate(vals)]


def _no_tokens(args: dict[str, Any]) -> None:
    """The media-token fields their doc names are refused honestly - the upload endpoints behind
    them are not in the public doc, so this lane passes URL inputs only."""
    present = [f for f in _TOKEN_FIELDS if args.get(f) not in (None, "", [])]
    if present:
        raise ValueError(f"media-token inputs ({', '.join(present)}) are not supported by this "
                         f"lane - it passes reference URL inputs only (their own rule: "
                         f"'{_TOKENS_RULE}'); media tokens ride the ArtCraft desktop app")


# ---------------------------------------------------------------- THE network seam

async def _http(method: str, url: str, *, api_key: str,
                json_body: dict | None = None) -> tuple[int, Any]:
    """The ONE seam every request rides. Raises _Upstream on any failure; returns
    (status, parsed-json-or-text). Tests monkeypatch exactly this - the suite stays offline."""
    import httpx                                     # lazy - the P1 no-network-import law
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S, follow_redirects=False,
                                     headers=_headers(api_key)) as cl:
            r = await (cl.post(url, json=json_body) if method == "POST" else cl.get(url))
            try:
                data: Any = r.json()
            except Exception:
                data = r.text
            return r.status_code, data
    except Exception as e:                            # noqa: BLE001 - the seam's own belt
        raise _Upstream(f"the ArtCraft API did not answer: {_clean(e, 140)}") from e


async def _call(method: str, path: str, *, api_key: str,
                json_body: dict | None = None) -> tuple[int, Any]:
    """The seam + the one honest status table (401 / 402 / other >=400)."""
    status, data = await _http(method, f"{_base()}{path}", api_key=api_key, json_body=json_body)
    if status == 401:
        raise _Upstream("their API answered 401 Unauthorized - the key is invalid, revoked, or "
                        "the account is banned", status=401)
    if status == 402:
        raise _Upstream("their API answered 402 Payment Required - the account is out of credits "
                        "(a refused generation spends nothing; top up at app.getartcraft.com)",
                        status=402)
    if status >= 400:
        raise _Upstream(f"their API answered {status}: "
                        f"{_clean(data if isinstance(data, str) else json.dumps(data), 200)}",
                        status=status)
    return status, data


# ---------------------------------------------------------------- the mappings (their states, honest)

def _map_state(state: dict) -> dict:
    """Their job state -> the lane's honest job fields. `done` = terminal; `job_ok` = success."""
    st = state.get("status") if isinstance(state, dict) else None
    status = str((st or {}).get("status") or "unknown")
    progress = (st or {}).get("progress_percentage")
    done = status in (_TERMINAL_OK, *_TERMINAL_BAD)
    out: dict[str, Any] = {"job_token": str(state.get("job_token") or ""),
                           "job_status": status, "done": done,
                           "job_ok": status == _TERMINAL_OK,
                           "progress": int(progress) if isinstance(progress, (int, float)) else None,
                           "failure_category": (st or {}).get("maybe_failure_category")}
    res = state.get("maybe_result")
    if isinstance(res, dict):
        links = res.get("media_links") if isinstance(res.get("media_links"), dict) else {}
        out["entity_token"] = res.get("entity_token")
        out["cdn_url"] = links.get("cdn_url")
        prev = links.get("maybe_video_previews")
        if isinstance(prev, dict):
            out["previews"] = {"still": prev.get("still"), "animated": prev.get("animated")}
        tpl = links.get("maybe_thumbnail_template")
        if tpl:
            out["thumbnail_template"] = tpl
    for k in ("created_at", "updated_at"):
        if state.get(k):
            out[k] = state.get(k)
    return out


def _job_note(mapped: dict) -> str:
    if mapped["job_ok"]:
        return "Generation complete - the finished media is at cdn_url."
    if mapped["done"]:
        return (f"The job ended without a result ({mapped['job_status']}"
                f"{' - ' + str(mapped['failure_category']) if mapped.get('failure_category') else ''}). "
                "A failed generation may still have spent credits - their rules, not ours.")
    return (f"Still running ({mapped['job_status']}"
            f"{', ' + str(mapped['progress']) + '%' if mapped.get('progress') is not None else ''}) - "
            "poll again with action=job and this token.")


# ---------------------------------------------------------------- the actions

def _act_status() -> dict:
    key = _key()
    out: dict[str, Any] = {
        "lane": "SHILP MANCH (v0.730) - the ArtCraft generation lane (Omni API, BYOK)",
        "actions": list(_SH_ACTIONS),
        "upstream": {"product": "ArtCraft (github.com/storytold/artcraft, MIT/Apache-2.0)",
                     "api": "the Omni API (their _docs/artcraft_omni_api.md)",
                     "base_url": _base(), "auth": "Authorization: Bearer <key>, never a cookie"},
        "key_set": bool(key),
        "caps": {"prompt_chars": _MAX_PROMPT, "refs_per_field": _MAX_REFS,
                 "ref_url_chars": _MAX_REF_URL, "batch_tokens": _MAX_TOKENS,
                 "timeout_s": _TIMEOUT_S},
        "laws": ["BYOK - the key lives in the VPS .env, never in chat or the repo",
                 "every generate call spends the account's credits - only on her explicit ask",
                 "a 402 (PAYMENT) is final - never retried",
                 "idempotency is minted here - a fresh UUID per call, never caller-supplied",
                 "reference urls cross the lane's wall first: http(s), no credentials, "
                 "no loopback/private/metadata hosts",
                 "only their documented endpoints ride here - nothing inferred",
                 "job states ride raw; `ok` is the call, `job_ok` is the job"],
        "v1_surface": "video + image generation, job + batch job status; audio/mesh/splat have "
                      "no documented Omni API endpoint yet",
    }
    if not key:
        out["note"] = ("no ArtCraft API key on this server - every network action answers "
                       "NEED_SETUP until one is set")
        out["setup"] = ("Create an API key at https://app.getartcraft.com/ (Account -> Settings "
                        "-> API Keys; API access is gated per account by the ArtCraft team), "
                        "then set ARTCRAFT_API_KEY in the VPS .env and restart. The key is shown "
                        "once - store it in the .env, never in chat or the repo.")
    return out


def _act_models() -> dict:
    counts = {k: sum(len(v) for v in fams.values()) for k, fams in _MODELS.items()}
    return {"catalog_source": "their public README (github.com/storytold/artcraft), curated 2026-11-09",
            "counts": counts, "total": sum(counts.values()),
            "catalog": {k: fams for k, fams in _MODELS.items()},
            "api_note": ("Omni API model ids are snake_case (their doc's example: seedance_2p0); "
                         "this list carries display names - an id their API does not know comes "
                         "back as their own 400, passed through unchanged"),
            "note": _MODELS_NOTE}


def _gen_body(args: dict[str, Any], kind: str) -> dict:
    """The generate request body - URL inputs only, caps refuse, idempotency minted here."""
    model = _clean(args.get("model"), _MAX_MODEL)
    if not model or not _MODEL_RE.match(model):
        raise ValueError(f"model must be a snake_case model id like 'seedance_2p0' (2-64 chars: "
                         f"letters, digits, underscore) - got '{_clip(args.get('model'), 60)}'; "
                         f"action=models shows the curated catalog")
    body: dict[str, Any] = {"model": model, "idempotency_token": str(uuid.uuid4())}
    prompt = args.get("prompt")
    if prompt:
        prompt = str(prompt)
        if len(prompt) > _MAX_PROMPT:
            raise ValueError(f"prompt is {len(prompt)} chars - past the {_MAX_PROMPT} cap")
        body["prompt"] = prompt
    if kind == "video":
        dur = args.get("duration_seconds")
        if dur is not None:
            try:
                body["duration_seconds"] = int(dur)
            except (TypeError, ValueError):
                raise ValueError(f"duration_seconds must be a whole number of seconds - got "
                                 f"'{_clip(dur, 40)}'")
        for f in ("aspect_ratio", "negative_prompt", "resolution"):
            v = args.get(f)
            if v:
                body[f] = _clean(v, 200)
        ga = args.get("generate_audio")
        if ga is not None:
            body["generate_audio"] = bool(ga)
        if args.get("start_frame_image_url"):
            body["start_frame_image_url"] = _ref_url(args.get("start_frame_image_url"),
                                                     "start_frame_image_url")
        if args.get("end_frame_image_url"):
            body["end_frame_image_url"] = _ref_url(args.get("end_frame_image_url"),
                                                   "end_frame_image_url")
        for field in ("reference_image_urls", "reference_video_urls", "reference_audio_urls"):
            refs = _ref_urls(args.get(field), field)
            if refs:
                body[field] = refs
    elif kind == "image":
        refs = _ref_urls(args.get("image_urls"), "image_urls")
        if refs:
            body["image_urls"] = refs
    return body


async def _generate(args: dict[str, Any], kind: str) -> dict:
    """action=video / action=image - one POST, one job token, credits spent."""
    key = _key()
    if not key:
        raise _NoKey()
    _no_tokens(args)
    body = _gen_body(args, kind)
    _, data = await _call("POST", f"/v1/omni_api/generate/{kind}", api_key=key, json_body=body)
    if not isinstance(data, dict) or not data.get("success"):
        raise _Upstream("their API answer was not a successful generation response")
    token = str(data.get("inference_job_token") or "")
    return {"job_token": token,
            "all_job_tokens": [str(t) for t in (data.get("all_job_tokens") or []) if t],
            "idempotency_token": body["idempotency_token"], "model": body["model"], "kind": kind,
            "note": ("Generation started - poll with action=job and this token (a batch can "
                     "carry several; all_job_tokens lists every one). The finished media lands "
                     "at cdn_url on complete_success. This call spent credits.")}


async def _act_job(token: str) -> dict:
    """action=job - one token, polled to their truth."""
    token = _clean(token, 80)
    if not _JOB_RE.match(token):
        raise ValueError(f"a job token looks like 'jinf_...' (lowercase letters and digits after "
                         f"the prefix) - got '{_clip(token, 60)}'; action=video / action=image "
                         f"returns one")
    key = _key()
    if not key:
        raise _NoKey()
    _, data = await _call("GET", f"/v1/omni_api/job_status/job/{token}", api_key=key)
    state = data.get("state") if isinstance(data, dict) else None
    if not isinstance(state, dict):
        raise _Upstream("their API answer had no job state")
    mapped = _map_state(state)
    mapped["note"] = _job_note(mapped)
    return mapped


async def _act_jobs(tokens: Any) -> dict:
    """action=jobs - the batch status, capped honestly."""
    key = _key()
    if not key:
        raise _NoKey()
    if not isinstance(tokens, (list, tuple)) or not tokens:
        raise ValueError("jobs needs a list of job tokens (tokens=[...]) - one or more, "
                         "from action=video / action=image")
    toks = [_clean(t, 80) for t in tokens if str(t or "").strip()]
    if len(toks) > _MAX_TOKENS:
        raise ValueError(f"{len(toks)} tokens - past the {_MAX_TOKENS} batch cap (poll the rest "
                         f"in a second call)")
    for t in toks:
        if not _JOB_RE.match(t):
            raise ValueError(f"a job token looks like 'jinf_...' - got '{_clip(t, 60)}'")
    qs = "&".join(f"tokens={t}" for t in toks)
    _, data = await _call("GET", f"/v1/omni_api/job_status/batch?{qs}", api_key=key)
    states = data.get("job_states") if isinstance(data, dict) else None
    if not isinstance(states, list):
        raise _Upstream("their API answer had no job_states list")
    mapped = [_map_state(s) if isinstance(s, dict) else {"job_status": "unknown", "done": False,
                                                         "job_ok": False} for s in states]
    running = sum(1 for m in mapped if not m["done"])
    ok = sum(1 for m in mapped if m["job_ok"])
    out = {"count": len(mapped), "jobs": mapped,
           "note": (f"{ok} complete, {running} still running, {len(mapped) - ok - running} ended "
                    f"without a result - poll running ones again with action=jobs.")}
    return out


# ---------------------------------------------------------------- error mapping (one honest table)

_NO_KEY_MSG = ("no ArtCraft API key on this server - generation and job status need one")
_NO_KEY_HINT = ("Create an API key at https://app.getartcraft.com/ (Account -> Settings -> API "
                "Keys; API access is gated per account by the ArtCraft team), then set "
                "ARTCRAFT_API_KEY in the VPS .env and restart.")


def _error_of(e: Exception) -> tuple[str, str, str]:
    if isinstance(e, _NoKey):
        return (NEED_SETUP, _NO_KEY_MSG, _NO_KEY_HINT)
    if isinstance(e, _Refused):
        return (NOT_ALLOWED, str(e), "reference urls are data leaving the box - public http(s) "
                                     "addresses only; the wall rides in action=status laws")
    if isinstance(e, _Upstream):
        if e.status == 401:
            return (AUTH, str(e), "check ARTCRAFT_API_KEY in the VPS .env (and that the account "
                                  "still has API access); the key is never shown here")
        if e.status == 402:
            return (PAYMENT, str(e), "FINAL - the lane never retries a payment refusal; top up "
                                     "credits at app.getartcraft.com, then ask again")
        return (UPSTREAM, str(e), "their API is down, slow or unhappy - try again shortly; "
                                  "action=job with the same token resumes the watch")
    if isinstance(e, ValueError):
        return (BAD_INPUT, str(e), "fix the argument the message names; action=models shows the "
                                   "curated catalog, action=status the caps")
    return (UPSTREAM, f"the shilp lane failed: {_clean(e, 160)}",
            "try the action again; if it repeats, action=status shows the lane's state")


# ---------------------------------------------------------------- envelope (the discipline)

def _envelope(action: str, error: tuple[str, str, str] | None = None, elapsed_ms: int = 0,
              **fields) -> dict:
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "ok": error is None, "tool": "shilp",
                           "action": action,
                           "error": (None if error is None else
                                     {"code": error[0], "message": error[1], "hint": error[2]})}
    out.update(fields)
    meta = dict(out.pop("meta", {}) or {})
    out["meta"] = {"elapsed_ms": max(0, int(elapsed_ms)),
                   "backend": BACKENDS.get(action, "ArtCraft Omni API (BYOK)"), **meta}
    return out


def _bad(action: str, msg: str, hint: str = "", code: str = BAD_INPUT) -> dict:
    return _envelope(action, error=(code, msg, hint))


def _locked(action: str) -> dict | None:
    if not _enabled():
        return _envelope(action, error=(
            NEED_SETUP, "the shilp generation lane is turned off on this server",
            "Ask the owner to set shilp_enabled=true."))
    return None


# ---------------------------------------------------------------- the ONE tool

async def shilp(ctx: Ctx, action: str = "status", *, model: str | None = None,
                prompt: str | None = None, duration_seconds: int | None = None,
                aspect_ratio: str | None = None, negative_prompt: str | None = None,
                resolution: str | None = None, generate_audio: bool | None = None,
                start_frame_image_url: str | None = None, end_frame_image_url: str | None = None,
                reference_image_urls: list | None = None,
                reference_video_urls: list | None = None,
                reference_audio_urls: list | None = None, image_urls: list | None = None,
                token: str | None = None, tokens: list | None = None,
                # the media-token fields their doc names - accepted only to be refused BY NAME
                # (the upload endpoints behind them are not in the public doc; nothing invented)
                start_frame_image_media_token: str | None = None,
                end_frame_image_media_token: str | None = None,
                reference_image_media_tokens: list | None = None,
                reference_video_media_tokens: list | None = None,
                reference_audio_media_tokens: list | None = None,
                image_media_tokens: list | None = None, **_) -> dict:
    """The ArtCraft generation door. Never raises; every answer is one envelope."""
    started = time.monotonic()
    action = str(action or "").strip().lower()
    if action not in _SH_ACTIONS:
        out = _bad(action or "", f"unknown action '{action}'; valid: {', '.join(_SH_ACTIONS)}",
                   "action=status shows the lane")
    elif (lock := _locked(action)) is not None:
        out = lock
    else:
        args = {"model": model, "prompt": prompt, "duration_seconds": duration_seconds,
                "aspect_ratio": aspect_ratio, "negative_prompt": negative_prompt,
                "resolution": resolution, "generate_audio": generate_audio,
                "start_frame_image_url": start_frame_image_url,
                "end_frame_image_url": end_frame_image_url,
                "reference_image_urls": reference_image_urls,
                "reference_video_urls": reference_video_urls,
                "reference_audio_urls": reference_audio_urls, "image_urls": image_urls,
                "token": token, "tokens": tokens,
                "start_frame_image_media_token": start_frame_image_media_token,
                "end_frame_image_media_token": end_frame_image_media_token,
                "reference_image_media_tokens": reference_image_media_tokens,
                "reference_video_media_tokens": reference_video_media_tokens,
                "reference_audio_media_tokens": reference_audio_media_tokens,
                "image_media_tokens": image_media_tokens}
        try:
            if action == "status":
                res = _act_status()
            elif action == "models":
                res = _act_models()
            elif action == "video":
                res = await _generate(args, "video")
            elif action == "image":
                res = await _generate(args, "image")
            elif action == "job":
                res = await _act_job(str(token or ""))
            elif action == "jobs":
                res = await _act_jobs(tokens)
            else:                                      # pragma: no cover - the enum is checked above
                raise ValueError(f"unknown action '{action}'")
            out = _envelope(action, **res) if isinstance(res, dict) else _envelope(action)
        except Exception as e:                         # noqa: BLE001 - one honest table
            out = _envelope(action, error=_error_of(e))
    out["meta"]["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return out


# ---------------------------------------------------------------- the sync door (MCP dispatch)

def _sync(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    """The MCP door dispatches through THIS - one path with the tool door, no drift."""
    return asyncio.run(shilp(ctx, action, **{k: v for k, v in (a or {}).items() if k != "action"}))


# ---------------------------------------------------------------- the tool spec the model sees

SHILP_TOOLS = [
    {"name": "shilp", "description": (
        "SHILP MANCH (v0.730): ArtCraft generation via their Omni API (api.storyteller.ai, BYOK) "
        "- images and video from a 62-model catalog (Seedance, Kling, Veo, Sora, Nano Banana, "
        "FLUX, Seedream, ...). Actions: status (the lane's key state, base url, caps and laws, "
        "zero network) | models (the curated README catalog, zero network) | video (start a video "
        "generation: model, prompt, duration_seconds, aspect_ratio, optional start/end frame and "
        "reference image/video/audio URLs - returns a job token) | image (start an image "
        "generation: model, prompt, optional image_urls) | job (poll one jinf_ token to their "
        "truth: progress, cdn_url on success) | jobs (batch-poll up to 25 tokens). EVERY "
        "generation spends the account's ArtCraft credits - start one only on the user's EXPLICIT "
        "ask, and never retry a 402 (PAYMENT is final). The key lives in the VPS .env "
        "(ARTCRAFT_API_KEY) and is never shown; API access is gated per account by the ArtCraft "
        "team. Reference URLs are data leaving the box: public http(s) only, no credentials, no "
        "private hosts. Media-token inputs ride their desktop app - this lane passes URL inputs "
        "only. Every answer one envelope {ok, action, error:{code, message, hint}}; job states "
        "ride raw (`ok` is the call, `job_ok` is the job)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": list(_SH_ACTIONS),
                    "description": "status | models | video | image | job | jobs"},
         "model": {"type": "string", "description": "video / image: the snake_case model id, e.g. seedance_2p0 (action=models shows the catalog)"},
         "prompt": {"type": "string", "description": "video / image: what to make"},
         "duration_seconds": {"type": "integer", "description": "video: output length in seconds, e.g. 6"},
         "aspect_ratio": {"type": "string", "description": "video: e.g. wide_sixteen_by_nine, tall_nine_by_sixteen, square"},
         "negative_prompt": {"type": "string", "description": "video: what to avoid"},
         "resolution": {"type": "string", "description": "video: e.g. seven_twenty_p, ten_eighty_p"},
         "generate_audio": {"type": "boolean", "description": "video: whether the model also makes sound"},
         "start_frame_image_url": {"type": "string", "description": "video: public http(s) url of the starting keyframe"},
         "end_frame_image_url": {"type": "string", "description": "video: public http(s) url of the ending keyframe"},
         "reference_image_urls": {"type": "array", "items": {"type": "string"},
                                  "description": "video: public http(s) reference image urls (max 20)"},
         "reference_video_urls": {"type": "array", "items": {"type": "string"},
                                  "description": "video: public http(s) reference mp4 urls (max 20)"},
         "reference_audio_urls": {"type": "array", "items": {"type": "string"},
                                  "description": "video: public http(s) reference audio urls (max 20)"},
         "image_urls": {"type": "array", "items": {"type": "string"},
                        "description": "image: public http(s) reference image urls (max 20)"},
         "token": {"type": "string", "description": "job: one jinf_ job token"},
         "tokens": {"type": "array", "items": {"type": "string"},
                    "description": "jobs: up to 25 jinf_ job tokens"}}}},
]

SHILP_LABELS = {"shilp": "Shilp: ArtCraft image/video generation (their Omni API; spends credits; BYOK)"}
SHILP_HANDLERS = {"shilp": shilp}
