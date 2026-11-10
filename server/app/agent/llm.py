"""Which brain answers a chat turn.

Santosh keeps every conversation in Anthropic's message format (text / tool_use / tool_result blocks).
For a low-cost brain, any OpenAI-compatible chat API can be used instead: Z.ai GLM by default, or a
self-hosted GLM (vLLM / SGLang) in an Indian data centre — only GLM_BASE_URL changes.

OmniRoute (open-source LLM gateway, runs next to Santosh on the VPS) sits in front of many providers and switches
between them by itself (combos, fallback, cost routing). Santosh then talks to one address.

Routing (CHAT_LLM):
  auto       OmniRoute when OMNIROUTE_URL is set, else GLM when GLM_API_KEY is set, else Claude
  omniroute  always OmniRoute (Claude only as fallback when it is down)
  glm        always GLM (Claude only as fallback)
  claude     always Claude
Claude is also used when a turn carries images/documents, or after the cheap brain fails, so an outage never
leaves the user without an answer. Safety never depends on the model: payments and messages stay frozen
server-side until the user approves them in the app.
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import re
import uuid

import httpx

from ..config import get_settings

log = logging.getLogger("santosh.llm")

_http: httpx.AsyncClient | None = None


def set_http(client: httpx.AsyncClient | None) -> None:
    global _http
    _http = client


# SAB GLM safety switch: her first live NVIDIA test listed the model but every chat call hung 120 s with 0 bytes. A hung
# brain must never make every turn wait out its timeout before Claude answers: after `glm_breaker_fails` failures in
# a row GLM is skipped for `glm_pause_s` (Claude answers at once), then tried again; one GLM request waits at most
# `glm_timeout_s`, and a timed-out request is not retried (a hung endpoint does not answer a second later).
# OMNIROUTE SAB KE LIYE: the same switch for each OpenAI-style brain (OmniRoute too), its own counters per brain.
BREAKERS: dict[str, dict] = {"glm": {"fails": 0, "until": 0.0, "paused": 0},
                             "omniroute": {"fails": 0, "until": 0.0, "paused": 0}}
BREAKER = BREAKERS["glm"]          # the GLM one, by its old name


def brain_paused(brain: str) -> bool:
    import time as _t
    b = BREAKERS.get(brain)
    return bool(b) and _t.time() < b["until"]


def brain_result(brain: str, ok: bool) -> None:
    import time as _t
    b = BREAKERS.get(brain)
    if b is None:
        return
    if ok:
        b["fails"] = 0
        return
    b["fails"] += 1
    st = get_settings()
    if b["fails"] >= max(1, int(getattr(st, "glm_breaker_fails", 2) or 2)):
        b["until"] = _t.time() + float(getattr(st, "glm_pause_s", 600) or 600)
        b["fails"] = 0
        b["paused"] += 1
        log.error("%s failed %s times in a row - skipped for %.0f s, Claude answers meanwhile", brain,
                  getattr(st, "glm_breaker_fails", 2), float(getattr(st, "glm_pause_s", 600) or 600))


def glm_paused() -> bool:
    return brain_paused("glm")


def glm_result(ok: bool) -> None:
    brain_result("glm", ok)


def _glm_timeout():
    t = float(getattr(get_settings(), "glm_timeout_s", 45) or 45)
    return httpx.Timeout(t, connect=10)


def _brain_timeout(label: str):
    """The clock for one request: GLM 45 s; OmniRoute 90 s (it may try two providers inside one request)."""
    if label.startswith("GLM"):
        return {"timeout": _glm_timeout()}
    if label.startswith("OmniRoute"):
        return {"timeout": httpx.Timeout(float(getattr(get_settings(), "omniroute_timeout_s", 90) or 90), connect=10)}
    return {}


def pause_refuses(brain: str) -> bool:
    """v0.736 the safety switch refuses a call only when another model may take it. While one model is the chat's
    model (chat_one_model) there is no other model: a paused GLM is still asked (v0.735 photo turn: every turn failed
    for 10 minutes with 'something went wrong'); `glm_pause_one_model` = true brings back the old refusal."""
    if not brain_paused(brain):
        return False
    try:
        st = get_settings()
        if one_model() and not bool(getattr(st, "glm_pause_one_model", False)):
            STATS["pause_ignored"] = STATS.get("pause_ignored", 0) + 1
            return False
    except Exception:
        pass
    return True


async def openai_create(brain: str, system: str, tools: list[dict], messages: list[dict],
                        max_tokens: int) -> tuple[list[dict], str, dict]:
    if pause_refuses(brain):
        raise LLMError(f"{brain} paused after repeated failures - another brain answers")
    try:
        out = await _openai_create(brain, system, tools, messages, max_tokens)
    except Exception:
        brain_result(brain, False)
        raise
    brain_result(brain, True)
    return out


async def openai_stream(brain: str, system: str, tools: list[dict], messages: list[dict], max_tokens: int,
                        on_text, on_think=None, on_tool=None) -> tuple[list[dict], str, dict]:
    if pause_refuses(brain):
        raise LLMError(f"{brain} paused after repeated failures - another brain answers")
    try:
        out = await _openai_stream(brain, system, tools, messages, max_tokens, on_text, on_think, on_tool)
    except Exception:
        brain_result(brain, False)
        raise
    brain_result(brain, True)
    return out


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=httpx.Timeout(90, connect=15))
    return _http


def glm_ready() -> bool:
    """v0.742 GLM_MODEL may name another provider ("aihubmix:coding-glm-5.3-flash-free"): its key counts."""
    try:
        from . import providers as _pv
        return _pv.ready(get_settings().glm_model or "")
    except Exception:
        return bool(get_settings().glm_api_key)


def model_in_force() -> str:
    """The model this call runs on: her dropdown pick, else GLM_MODEL from .env."""
    return MODEL_NOW.get() or (get_settings().glm_model or "")


def omniroute_ready() -> bool:
    return bool(get_settings().omniroute_url)


def cheap_brain() -> str | None:
    """The OpenAI-compatible brain configured for chat, or None for Claude only."""
    st = get_settings()
    mode = (st.chat_llm or "auto").lower()
    if mode == "claude":
        return None
    if mode == "omniroute":
        return "omniroute" if omniroute_ready() and not brain_paused("omniroute") else None
    if mode == "glm":
        return "glm" if glm_ready() and not glm_paused() else None
    if omniroute_ready() and not brain_paused("omniroute"):
        return "omniroute"
    return "glm" if glm_ready() and not glm_paused() else None


def one_model() -> bool:
    """v0.732 PARITY PHASE 1: a chat turn stays on one model (chat_one_model)."""
    try:
        return bool(getattr(get_settings(), "chat_one_model", True))
    except Exception:
        return True


def chat_brain() -> str | None:
    """The brain a chat runs on: like cheap_brain, but a brain the safety switch paused is STILL the chat's brain while
    chat_one_model is on (a pause sends background calls to Claude; it never moves a chat to another model)."""
    if not one_model():
        return cheap_brain()
    st = get_settings()
    mode = (st.chat_llm or "auto").lower()
    if mode == "claude":
        return None
    if mode == "omniroute":
        return "omniroute" if omniroute_ready() else None
    if mode == "glm":
        return "glm" if glm_ready() else None
    if omniroute_ready():
        return "omniroute"
    return "glm" if glm_ready() else None


def describe() -> str:
    st = get_settings()
    b = chat_brain() if one_model() else cheap_brain()   # v0.736 healthz names the chat's real model
    tail = " (paused)" if b and brain_paused(b) else ""
    if b == "omniroute":
        return "omniroute:" + st.omniroute_model + tail
    if b == "glm":
        return "glm:" + st.glm_model + tail
    return "claude"


def choose(messages: list[dict]) -> str:
    """'omniroute', 'glm' or 'claude' for this turn."""
    st = get_settings()
    b = chat_brain()
    if b is None:
        return "claude"
    if _has_media(messages[-1:]) and st.anthropic_api_key and not glm_handles(messages[-1:], b):
        return "claude"          # pictures and PDFs go to the model that reads them well (NVIDIA GLM reads pictures)
    return b


def glm_reads_images(b: str = "glm") -> bool:
    """v0.735 ALL GLM: GLM reads pictures on NVIDIA and on OpenRouter (z-ai/glm-5.3-flash: text + image + video)."""
    try:
        st = get_settings()
        if b != "glm":
            return False
        if not bool(getattr(st, "glm_images", False)) and not is_nvidia():
            return False
        from . import modelprofile as _mp          # v0.739 the model's own list says whether it reads pictures
        r = _mp.reads("image")
        if r is not None:
            return r
        from . import providers as _pv
        if _pv.split(model_in_force())[0]:
            return False                           # v0.741 another provider's model nobody could describe: text only
        return is_nvidia() or bool(getattr(st, "glm_images", False))
    except Exception:
        return False


def glm_reads_pdfs(b: str = "glm") -> bool:
    try:
        return b == "glm" and bool(getattr(get_settings(), "glm_pdf", False))
    except Exception:
        return False


def glm_handles(messages: list[dict], b: str = "glm") -> bool:
    """True when every picture / PDF in these messages can go to the GLM brain itself."""
    for m in messages:
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for blk in c:
            k = blk.get("type") if isinstance(blk, dict) else None
            if k == "image" and not glm_reads_images(b):
                return False
            if k == "document" and not glm_reads_pdfs(b):
                return False
    return True


def pdf_parts(block: dict) -> list[dict]:
    """v0.735 ALL GLM: one Anthropic 'document' block (a base64 PDF) -> OpenAI parts GLM can read: the PDF's own text
    (pypdf), or - when it has almost no text (a scan) - its first pages as pictures (pypdfium2). Never raises."""
    import base64
    import io
    st = get_settings()
    src = (block or {}).get("source") or {}
    title = str((block or {}).get("title") or "the attached PDF")
    if src.get("type") == "text" and src.get("data"):
        return [{"type": "text", "text": f"--- {title} (text) ---\n{str(src['data'])[:int(st.glm_pdf_max_chars)]}"}]
    if src.get("type") != "base64" or not src.get("data"):
        return [{"type": "text", "text": f"[{title}: a PDF that could not be opened here]"}]
    try:
        raw = base64.b64decode(src["data"])
    except Exception:
        return [{"type": "text", "text": f"[{title}: the PDF could not be decoded]"}]
    text, pages = "", 0
    try:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(raw))
        pages = len(rd.pages)
        chunks = []
        for i, pg in enumerate(rd.pages):
            chunks.append(f"[page {i + 1}]\n" + (pg.extract_text() or "").strip())
            if sum(len(x) for x in chunks) > int(st.glm_pdf_max_chars):
                break
        text = "\n\n".join(chunks)[:int(st.glm_pdf_max_chars)]
    except Exception as e:   # noqa: BLE001
        log.info("pdf text failed: %s", str(e)[:120])
    words = len(re.findall(r"\w+", re.sub(r"\[page \d+\]", "", text)))
    if words >= 20 * max(1, min(pages, 3)):
        return [{"type": "text", "text": f"--- {title} ({pages} pages, its text) ---\n{text}"}]
    if not glm_reads_images("glm"):   # v0.739 a model that cannot see pictures gets the little text there is, said plainly
        return [{"type": "text", "text": f"--- {title}: a scanned PDF ({pages or '?'} pages); this model cannot read its "
                 f"page pictures, so only its own text is here ---\n{text}"}]
    out: list[dict] = [{"type": "text", "text": f"--- {title}: a scanned PDF ({pages or '?'} pages), its pages as pictures ---"}]
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(raw)
        for i in range(min(len(doc), int(st.glm_pdf_max_pages))):
            img = doc[i].render(scale=1.6).to_pil()
            buf = io.BytesIO()
            img.convert("RGB").save(buf, "JPEG", quality=82)
            out.append({"type": "image_url", "image_url": {
                "url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}})
    except Exception as e:   # noqa: BLE001
        log.info("pdf pages to pictures failed: %s", str(e)[:120])
        out.append({"type": "text", "text": text or f"[{title}: no readable text and its pages could not be drawn]"})
    return out


def _only_images(messages: list[dict]) -> bool:
    for m in messages:
        c = m.get("content")
        if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "document" for b in c):
            return False
    return True


def _has_media(messages: list[dict]) -> bool:
    for m in messages:
        c = m.get("content")
        if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") in ("image", "document") for b in c):
            return True
    return False


# ---------------- Anthropic blocks <-> OpenAI chat format ----------------
def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    out = []
    for b in content or []:
        if isinstance(b, dict) and b.get("type") == "text":
            out.append(b.get("text", ""))
        elif isinstance(b, dict) and b.get("type") in ("image", "document"):
            out.append("[attachment]")
    return "\n".join(t for t in out if t)


def _image_parts(blocks: list) -> list[dict]:
    """Anthropic base64 image blocks -> OpenAI image_url parts, only for a brain that reads pictures (NVIDIA GLM;
    v0.735 also GLM on OpenRouter with glm_images)."""
    try:
        if not glm_reads_images("glm"):
            return []
    except Exception:
        return []
    out = []
    for b in blocks:
        if not (isinstance(b, dict) and b.get("type") == "image"):
            continue
        src = b.get("source") or {}
        if src.get("type") == "base64" and src.get("data"):
            out.append({"type": "image_url",
                        "image_url": {"url": f"data:{src.get('media_type') or 'image/png'};base64,{src['data']}"}})
        elif src.get("type") == "url" and src.get("url"):
            out.append({"type": "image_url", "image_url": {"url": src["url"]}})
    return out[:8]


def to_openai(system: str, tools: list[dict], messages: list[dict]) -> tuple[list[dict], list[dict]]:
    msgs: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        c = m["content"]
        if m["role"] == "assistant":
            blocks = c if isinstance(c, list) else [{"type": "text", "text": c}]
            text = "\n\n".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
            calls = [{"id": b["id"], "type": "function",
                      "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {}, ensure_ascii=False)}}
                     for b in blocks if b.get("type") == "tool_use"]
            msg: dict = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            if text or calls:
                msgs.append(msg)
            continue
        if isinstance(c, str):
            msgs.append({"role": "user", "content": c})
            continue
        # tool results must come straight after the assistant's tool_calls; any extra text goes after them
        extra = []
        for b in c:
            if b.get("type") == "tool_result":
                body = b.get("content")
                body = body if isinstance(body, str) else _text_of(body)
                if b.get("is_error"):
                    body = f"ERROR: {body}"
                msgs.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": body})
            else:
                extra.append(b)
        if extra:
            parts = _image_parts(extra)
            if glm_reads_pdfs("glm") and any(b.get("type") == "document" for b in extra):
                docparts = [p for b in extra if b.get("type") == "document" for p in pdf_parts(b)]
                parts = parts + [p for p in docparts if p.get("type") == "image_url"]
                extra = [b for b in extra if b.get("type") != "document"] + [
                    {"type": "text", "text": p["text"]} for p in docparts if p.get("type") == "text"]
            t = _text_of([b for b in extra if not (parts and b.get("type") == "image")])
            if parts:       # SAB GLM: NVIDIA's GLM-5.3-Flash reads pictures (png / jpg / webp, up to 8 a request)
                msgs.append({"role": "user", "content": ([{"type": "text", "text": t}] if t else []) + parts})
            elif t:
                msgs.append({"role": "user", "content": t})
    fns = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                             "parameters": t.get("input_schema") or {"type": "object", "properties": {}}}}
           for t in tools]
    return msgs, fns


def from_openai(data: dict) -> tuple[list[dict], str]:
    ch = (data.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    blocks: list[dict] = []
    text = (msg.get("content") or "").strip()
    if text:
        blocks.append({"type": "text", "text": text})
    cut = (ch.get("finish_reason") or "") == "length"
    broken = 0
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
            if not isinstance(args, dict):
                args = {}
        except json.JSONDecodeError:
            # v0.221 half-written arguments = the answer was cut (some gateways never say "length"): never run a
            # tool with empty inputs - drop the call and let the turn continue where the cut happened.
            broken += 1
            STATS["broken_calls"] += 1
            continue
        tid = re.sub(r"[^a-zA-Z0-9_-]", "_", tc.get("id") or "") or f"call_{uuid.uuid4().hex[:12]}"
        blocks.append({"type": "tool_use", "id": tid,
                       "name": fn.get("name", ""), "input": args})
    if any(b["type"] == "tool_use" for b in blocks):
        stop = "tool_use"           # the whole calls run; the next step carries on
    elif cut or broken:
        stop = "max_tokens"         # v0.221 the cheap brain's cut answer is NOT a finished answer (was 'end_turn')
        STATS["cut"] += 1
    else:
        stop = "end_turn"
    return blocks, stop


STATS: dict[str, int] = {"cut": 0, "broken_calls": 0}   # v0.221 cut answers seen on the OpenAI-style brains


class LLMError(RuntimeError):
    pass


# a busy or briefly unreachable model is worth another try before the turn falls back to another brain
TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}
RETRY_DELAY = 0.6   # seconds; doubles each try (tests shorten it)


def _learn(**facts) -> None:
    try:
        from . import modelprofile as _mp
        _mp.learn(**facts)
    except Exception:
        pass


async def _post_with_retry(url: str, body: dict, headers: dict, label: str) -> httpx.Response:
    tries = 1 + max(0, get_settings().llm_retries)
    last: LLMError | None = None
    for i in range(tries):
        wait = RETRY_DELAY * (2 ** i)
        try:
            r = await _client().post(url, json=body, headers=headers,
                                     **_brain_timeout(label))
        except httpx.TimeoutException as e:
            if label.startswith("GLM"):
                raise LLMError(f"{label} not reachable: timed out ({type(e).__name__})") from e   # never retried
            last = LLMError(f"{label} not reachable: timed out ({type(e).__name__})")
        except httpx.HTTPError as e:
            last = LLMError(f"{label} not reachable: {type(e).__name__} {e}")
        else:
            if r.status_code < 400:
                return r
            last = LLMError(f"{label} error {r.status_code}: {r.text[:300]}")
            _rf = ("reasoning_effort", "chat_template_kwargs", "reasoning", "thinking")
            if r.status_code in (400, 422) and "mandatory" in r.text.lower() and "reasoning" in r.text.lower() \
                    and "reasoning" not in body and is_openrouter():
                # v0.739 the model says it cannot run without reasoning: ask again with it and remember it for this model
                body = {**body, "reasoning": {"effort": get_settings().glm_reasoning_effort or "low", "exclude": True}}
                _learn(reasoning_mandatory=True, reasoning_refused=False)
                log.warning("%s needs the reasoning field - asking again with it (remembered)", label)
                r = await _client().post(url, json=body, headers=headers)
                if r.status_code < 400:
                    return r
                last = LLMError(f"{label} error {r.status_code}: {r.text[:300]}")
            elif r.status_code in (400, 422) and any(k in body for k in _rf):
                body = {k: v for k, v in body.items() if k not in _rf}
                log.warning("%s refused the reasoning fields - asking again without them", label)
                r = await _client().post(url, json=body, headers=headers)
                if r.status_code < 400:
                    if is_openrouter():
                        _learn(reasoning_refused=True, reasoning_mandatory=False)
                    return r
                last = LLMError(f"{label} error {r.status_code}: {r.text[:300]}")
            if r.status_code not in TRANSIENT_STATUS:
                raise last   # a wrong key or a bad request will not get better by asking again
            ra = r.headers.get("retry-after", "")
            if ra.isdigit():
                wait = min(float(ra), 5.0)
        if i + 1 < tries:
            log.warning("%s (try %d of %d); retrying in %.1fs", last, i + 1, tries, min(wait, 5.0))
            await asyncio.sleep(min(wait, 5.0))
    assert last is not None
    raise last


# parity Phase 4 THINKING: the reasoning effort THIS chat turn asked for ('' = the old fixed settings: effort
# glm_reasoning_effort, reasoning text excluded). Set once per step by the chat loop (santosh._steps_inner) from the
# turn's kind - low for a greeting, medium for an ordinary ask, high for a hard ask / long job - and only while
# chat_thinking_adaptive is on. With a level the reasoning text streams back (exclude false) to the Soch card.
REASONING_NOW: contextvars.ContextVar[str] = contextvars.ContextVar("hoola_reasoning_now", default="")
# v0.740 the model THIS turn runs on, from her console dropdown (modelchoice); '' = GLM_MODEL from .env
MODEL_NOW: contextvars.ContextVar[str] = contextvars.ContextVar("hoola_model_now", default="")
LEVELS = ("low", "medium", "high")
_ROOM_X = {"low": 1, "medium": 2, "high": 4}   # reasoning room = glm_reasoning_room x this, so the answer is never starved


def reasoning_room(level: str = "") -> int:
    """Tokens added to max_tokens for the reasoning: the fixed glm_reasoning_room, or that x the turn's level."""
    base = max(0, int(getattr(get_settings(), "glm_reasoning_room", 2048) or 0))
    return base * _ROOM_X.get(level, 1)


def _target(brain: str) -> tuple[str, str, str, dict, dict]:
    """(url, model, label, headers, extra body) for an OpenAI-compatible brain."""
    st = get_settings()
    if brain == "glm":
        from . import providers as _pv
        _p, _slug = _pv.split(model_in_force())
        if _p and _p != "openrouter":
            # v0.741 MORE PROVIDERS: her pick names another provider - its own endpoint and key, and no provider-specific
            # reasoning field (each speaks its own; the plain request works everywhere)
            return (_pv.base_of(_p) + "/chat/completions", _slug, f"{_pv.label_of(_p)}",
                    {"Authorization": f"Bearer {_pv.key_of(_p)}"}, {})
        if _p == "openrouter":
            _lvl = REASONING_NOW.get()
            _ex = {"reasoning": {"effort": _lvl or st.glm_reasoning_effort or "low", "exclude": not _lvl}}
            if _reasoning_ok() is False:
                _ex = {}
            return (_pv.base_of(_p) + "/chat/completions", _slug, "OpenRouter",
                    {"Authorization": f"Bearer {_pv.key_of(_p)}"}, _ex)
    if brain == "omniroute":
        h = {"x-omniroute-compression": st.omniroute_compression or "off"}   # never rewrite Santosh's tool results
        if st.omniroute_key:
            h["Authorization"] = f"Bearer {st.omniroute_key}"
        return st.omniroute_url.rstrip("/") + "/chat/completions", st.omniroute_model, "OmniRoute", h, {}
    if is_nvidia():
        # SAB GLM: NVIDIA's hosted GLM-5.3-Flash always reasons (it cannot be switched off); the effort is set with
        # reasoning_effort (low | high | max, default max = slow) and chat turns ask clear_thinking (NVIDIA's own page).
        # Those two fields are GLM's own: another NVIDIA model (her key answered only Nemotron) gets a plain request.
        lvl = REASONING_NOW.get()
        nv = {"high": "high"}.get(lvl, "low") if lvl else ""     # NVIDIA GLM knows low | high | max (no medium)
        extra = ({"reasoning_effort": nv or st.glm_reasoning_effort or "low",
                  "chat_template_kwargs": {"clear_thinking": True}}
                 if "glm" in (MODEL_NOW.get() or st.glm_model or "").lower() else {})
        label = "GLM (NVIDIA)"
    elif is_openrouter():
        # v0.699 GLM VIA OPENROUTER: OpenRouter speaks its OWN reasoning field ({"reasoning": {...}}), not Z.ai's
        # "thinking". v0.700: her live check - z-ai/glm-5.3-flash on OpenRouter answers 400 "Reasoning is mandatory
        # for this endpoint and cannot be disabled", so reasoning is never switched off there: effort low (fast +
        # cheap), the reasoning text excluded from the reply, and room() adds space for it in max_tokens.
        lvl = REASONING_NOW.get()
        if lvl:
            # parity Phase 4: the turn's own effort, and the reasoning text comes back (never into the answer)
            extra = {"reasoning": {"effort": lvl, "exclude": False}}
        else:
            extra = {"reasoning": {"effort": st.glm_reasoning_effort or "low", "exclude": True}}
        if _reasoning_ok() is False:
            extra = {}    # v0.739 the model's own list says it takes no reasoning field: never send one
        label = "GLM (OpenRouter)"
    else:
        lvl = REASONING_NOW.get()
        if lvl in ("medium", "high"):
            extra = {"thinking": {"type": "enabled"}}     # parity Phase 4: Z.ai thinks on an ordinary / hard turn
        else:
            extra = {"thinking": {"type": st.glm_thinking}} if st.glm_thinking in ("enabled", "disabled") else {}
        label = "GLM"
    return (st.glm_base_url.rstrip("/") + "/chat/completions", MODEL_NOW.get() or st.glm_model, label,
            {"Authorization": f"Bearer {st.glm_api_key}"}, extra)


def is_nvidia() -> bool:
    try:   # v0.741 a prefixed pick runs on its own provider with a plain request (no GLM-only NVIDIA fields)
        from . import providers as _pv
        if _pv.split(model_in_force())[0]:
            return False
    except Exception:
        pass
    return "integrate.api.nvidia.com" in (get_settings().glm_base_url or "")


def is_openrouter() -> bool:
    try:   # v0.741 a turn on another provider (her pick) is not an OpenRouter call, whatever GLM_BASE_URL says
        from . import providers as _pv
        _p, _ = _pv.split(model_in_force())
        if _p:
            return _p == "openrouter"
    except Exception:
        pass
    return "openrouter.ai" in (get_settings().glm_base_url or "")


def _reasoning_ok() -> bool | None:
    try:
        from . import modelprofile as _mp
        return _mp.supports("reasoning")
    except Exception:
        return None


def room(max_tokens: int) -> int:
    """NVIDIA's GLM counts its (always-on) reasoning inside max_tokens: a 900-token reviewer would come back empty.
    Room for the reasoning is added on that endpoint only."""
    lvl = REASONING_NOW.get()
    if not (is_nvidia() or is_openrouter()):
        if lvl in ("medium", "high"):      # parity Phase 4: Z.ai with thinking on also counts it inside max_tokens
            return int(max_tokens) + reasoning_room(lvl)
        return max_tokens
    if is_openrouter() and _reasoning_ok() is False:
        return int(max_tokens)          # v0.739 a model that does not reason needs no room for it
    return int(max_tokens) + reasoning_room(lvl)


async def _openai_create(brain: str, system: str, tools: list[dict], messages: list[dict],
                         max_tokens: int) -> tuple[list[dict], str, dict]:
    st = get_settings()
    url, model, label, headers, extra = _target(brain)
    msgs, fns = to_openai(system, tools, messages)
    body: dict = {"model": model, "messages": msgs, "max_tokens": room(max_tokens) if brain == "glm" else max_tokens,
                  "temperature": st.glm_temperature, **extra}
    if fns:
        body["tools"] = fns
        body["tool_choice"] = "auto"
    r = await _post_with_retry(url, body, headers, label)
    try:
        data = r.json()
    except ValueError as e:
        raise LLMError(f"{label} sent a broken answer: {e}") from e
    blocks, stop = from_openai(data)
    if not blocks:
        raise LLMError(f"{label} returned an empty answer")
    usage = dict(data.get("usage") or {})
    route = r.headers.get("x-omniroute-decision")
    if route:
        usage["route"] = route
        usage["model"] = r.headers.get("x-omniroute-model", "")
    from .. import usage as _usage      # v0.98 the cheap brain is counted too
    _usage.from_openai(data.get("model") or model, usage)
    return blocks, stop, usage


def _stream_body(brain: str, system: str, tools: list[dict], messages: list[dict], max_tokens: int):
    st = get_settings()
    url, model, label, headers, extra = _target(brain)
    msgs, fns = to_openai(system, tools, messages)
    body: dict = {"model": model, "messages": msgs, "max_tokens": room(max_tokens) if brain == "glm" else max_tokens,
                  "temperature": st.glm_temperature, "stream": True, **extra}
    if fns:
        body["tools"] = fns
        body["tool_choice"] = "auto"
    return url, model, label, headers, body


def _assemble(text: str, calls: dict[int, dict], finish: str = "") -> dict:
    """The streamed pieces as one ordinary (non-stream) answer, so from_openai reads it the same way."""
    tcs = [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
           for _, c in sorted(calls.items())]
    msg: dict = {"content": text}
    if tcs:
        msg["tool_calls"] = tcs
    return {"choices": [{"message": msg, "finish_reason": finish or None}]}


async def _openai_stream(brain: str, system: str, tools: list[dict], messages: list[dict], max_tokens: int,
                         on_text, on_think=None, on_tool=None) -> tuple[list[dict], str, dict]:
    """v0.161 the same answer as openai_create, but the words reach `on_text` as the model writes them. Tool-call
    arguments are joined and parsed only when the answer is complete (never partial JSON). Retries only before the
    first word arrived (after that the caller resets the words and falls back to the other brain).
    v0.171 `reasoning_content` deltas (GLM thinking) go to `on_think` when the brain sends them; they are never
    part of the answer text."""
    url, model, label, headers, body = _stream_body(brain, system, tools, messages, max_tokens)
    tries = 1 + max(0, get_settings().llm_retries)
    for i in range(tries):
        wait = min(RETRY_DELAY * (2 ** i), 5.0)
        text: list[str] = []
        calls: dict[int, dict] = {}
        usage: dict = {}
        finish = ""
        try:
            async with _client().stream("POST", url, json=body, headers=headers,
                                        **_brain_timeout(label)) as r:
                if r.status_code >= 400:
                    detail = (await r.aread()).decode("utf-8", "replace")[:300]
                    err = LLMError(f"{label} error {r.status_code}: {detail}")
                    if r.status_code not in TRANSIENT_STATUS or i + 1 >= tries:
                        raise err
                    log.warning("%s (try %d of %d); retrying in %.1fs", err, i + 1, tries, wait)
                    await asyncio.sleep(wait)
                    continue
                route = r.headers.get("x-omniroute-decision")
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        j = json.loads(data)
                    except ValueError:
                        continue
                    if j.get("usage"):
                        usage = dict(j["usage"])
                    for ch in j.get("choices") or []:
                        if ch.get("finish_reason"):
                            finish = ch["finish_reason"]
                        d = ch.get("delta") or {}
                        if d.get("content"):
                            text.append(d["content"])
                            on_text(d["content"])
                        rc = d.get("reasoning_content") or d.get("reasoning")   # v0.171 thinking deltas
                        if rc and on_think:
                            on_think(rc)
                        for tc in d.get("tool_calls") or []:
                            c = calls.setdefault(int(tc.get("index") or 0), {"id": "", "name": "", "args": ""})
                            fn = tc.get("function") or {}
                            c["id"] = tc.get("id") or c["id"]
                            c["name"] += fn.get("name") or ""
                            c["args"] += fn.get("arguments") or ""
                            if on_tool and c["name"]:   # parity Phase 6: a page written in a tool call shows as it grows
                                try:
                                    on_tool(int(tc.get("index") or 0), c["name"], c["args"])
                                except Exception:
                                    pass
        except httpx.HTTPError as e:
            if text or i + 1 >= tries:
                raise LLMError(f"{label} not reachable: {e}") from e
            log.warning("%s not reachable (try %d of %d): %s", label, i + 1, tries, e)
            await asyncio.sleep(wait)
            continue
        blocks, stop = from_openai(_assemble("".join(text), calls, finish))
        if not blocks:
            raise LLMError(f"{label} returned an empty answer")
        if not usage:   # some gateways send no usage on streams: a fair estimate keeps the monthly limit honest
            usage = {"prompt_tokens": len(json.dumps(body["messages"], ensure_ascii=False)) // 4,
                     "completion_tokens": max(1, len(json.dumps(blocks, ensure_ascii=False)) // 4), "estimated": True}
        if route:
            usage["route"] = route
        from .. import usage as _usage
        _usage.from_openai(model, usage)
        return blocks, stop, usage
    raise LLMError(f"{label} returned no answer")


async def glm_create(system: str, tools: list[dict], messages: list[dict], max_tokens: int) -> tuple[list[dict], str, dict]:
    return await openai_create("glm", system, tools, messages, max_tokens)
