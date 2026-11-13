"""v0.851 PC BRAIN (owner: "FOR PC WE CURRENTLY CHOOSE 2 MODELS QWEN 3.8 AND SONET 5.5 --- WILL TEST IT FIRST ---
WILL START WITH QWEN"): the model that SEES her screen and picks the next click, chosen for the PC loop alone.

Two brains, one shape. The operator loop keeps speaking Anthropic's message format (text / image / tool_use /
tool_result blocks); this module turns one step into either
  - "qwen":   Qwen 3.8 Max through OpenRouter only (v0.853, owner: never Alibaba Cloud) on the server's OpenRouter key,
              model `pc_qwen_openrouter_model` (qwen/qwen3.8-max-0902). Screenshots ride as image_url data URIs; a tool result's
              screenshot is sent in the user message right after the tool messages (OpenAI tool messages are text).
  - "sonnet": Claude `pc_sonnet_model` (claude-sonnet-5-5) through the SDK, with the "everything on Haiku" rewrite
              (usage.one_model) and the GLM door both standing aside for this call - so the PC loop gets the model
              it names, not Haiku or GLM-Flash.
and hands back an object with `.content` (Anthropic-shaped dicts), `.stop` and `.model`.

No OpenRouter key = the step runs on Sonnet and the task says so once (op.brain_note) - never a silent swap.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from ..config import get_settings

log = logging.getLogger("santosh.pc")

BRAINS = ("qwen27", "qwen", "sonnet")
STATS: dict[str, int] = {"qwen27": 0, "qwen": 0, "sonnet": 0, "fallback": 0, "qwen_errors": 0}


@dataclass
class Reply:
    content: list[dict] = field(default_factory=list)
    stop: str = ""          # end_turn / tool_use / max_tokens / refusal (Anthropic words, Qwen's mapped onto them)
    model: str = ""


def norm(name: str) -> str:
    n = str(name or "").strip().lower()
    if n in ("qwen27", "qwen-27b", "qwen3.8-27b", "cheap", "sasta"):
        return "qwen27"      # v0.867 PC SASTA: the cheap worker
    if n.startswith("qwen"):
        return "qwen"
    if n.startswith(("sonnet", "claude")):
        return "sonnet"
    return ""


OPENROUTER = "https://openrouter.ai/api/v1"


def qwen_route() -> tuple[str, str, str] | None:
    """v0.853 (url, key, model) for Qwen - ONLY through OpenRouter (owner: "DONT GO VIA ALIBABA CLOUD GO VIA A OPENROUTER"),
    on the OpenRouter key the server already has; model `pc_qwen_openrouter_model` (qwen/qwen3.8-max-0902: screenshots +
    tools). None = no OpenRouter key."""
    st = get_settings()
    try:
        from ..agent.providers import key_of
        okey = key_of("openrouter")
    except Exception:
        okey = ""
    if not okey:
        return None
    return (OPENROUTER + "/chat/completions", okey,
            str(getattr(st, "pc_qwen_openrouter_model", "") or "qwen/qwen3.8-max-0902"))


def choose(want: str = "") -> tuple[str, str, str]:
    """(brain, model, note). `want` = this task's pick ('' = the server's pc_model). A Qwen pick with no key at all
    (no OpenRouter key) runs on Sonnet and says why in `note`."""
    st = get_settings()
    brain = norm(want) or norm(getattr(st, "pc_model", "")) or "sonnet"
    route = qwen_route() if brain in ("qwen", "qwen27") else None
    if brain in ("qwen", "qwen27") and route is None:
        STATS["fallback"] += 1
        return ("sonnet", str(getattr(st, "pc_sonnet_model", "") or "claude-sonnet-5-5"),
                "No OpenRouter key (OPENROUTER_API_KEY) is on the server, so this PC task ran on Sonnet 5.5 instead of Qwen.")
    if brain == "qwen27":
        # v0.867 PC SASTA (owner: "GO QWEN 27B"): the cheap worker, ~a tenth of Sonnet; rescue.py brings Sonnet in when it is stuck
        return "qwen27", str(getattr(st, "pc_cheap_model", "") or "qwen/qwen3.8-27b"), ""
    if brain == "qwen":
        return "qwen", route[2], ""
    if getattr(st, "pc_via_openrouter", True) and qwen_route() is not None:
        # v0.866 SONNET VIA OPENROUTER (owner: "I HAVE CREDIT IN OPENROUTER USE SONET VIA THAT"): the same Sonnet, billed
        # to her OpenRouter credit, over the OpenAI-shaped path the Qwen brain already uses
        return "sonnet-or", str(getattr(st, "pc_openrouter_sonnet", "") or "anthropic/claude-sonnet-5.5"), ""
    return "sonnet", str(getattr(st, "pc_sonnet_model", "") or "claude-sonnet-5-5"), ""


# ------------------------------------------------------------------ Anthropic blocks -> OpenAI chat messages
def _img_part(b: dict) -> dict | None:
    src = b.get("source") or {}
    if src.get("type") == "base64" and src.get("data"):
        return {"type": "image_url",
                "image_url": {"url": f"data:{src.get('media_type') or 'image/jpeg'};base64,{src['data']}"}}
    return None


def _flat(content: Any) -> tuple[str, list[dict]]:
    """A tool_result's content -> (its text, its images as image_url parts)."""
    if isinstance(content, str):
        return content, []
    texts, imgs = [], []
    for blk in content or []:
        if not isinstance(blk, dict):
            continue
        if blk.get("type") == "text":
            texts.append(str(blk.get("text") or ""))
        elif blk.get("type") == "image":
            p = _img_part(blk)
            if p:
                imgs.append(p)
    return "\n".join(t for t in texts if t.strip()), imgs


def to_openai(system: str, messages: list[dict]) -> list[dict]:
    out: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        content = m.get("content")
        if m.get("role") == "assistant":
            blocks = content if isinstance(content, list) else [{"type": "text", "text": str(content or "")}]
            text = " ".join(str(b.get("text") or "") for b in blocks if b.get("type") == "text").strip()
            calls = [{"id": b["id"], "type": "function",
                      "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {}, ensure_ascii=False)}}
                     for b in blocks if b.get("type") == "tool_use"]
            msg: dict[str, Any] = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
            continue
        if isinstance(content, str):
            out.append({"role": "user", "content": content})
            continue
        parts: list[dict] = []       # text + images that ride in a user message
        tools: list[dict] = []       # tool results, each its own role=tool message, BEFORE the user message
        for b in content or []:
            t = b.get("type")
            if t == "text":
                parts.append({"type": "text", "text": str(b.get("text") or "")})
            elif t == "image":
                p = _img_part(b)
                if p:
                    parts.append(p)
            elif t == "tool_result":
                text, imgs = _flat(b.get("content"))
                if b.get("is_error"):
                    text = "ERROR: " + text
                tools.append({"role": "tool", "tool_call_id": b.get("tool_use_id"), "content": text or "ok"})
                if imgs:
                    parts.append({"type": "text", "text": "Screen now:"})
                    parts.extend(imgs)
        out.extend(tools)
        if parts:
            out.append({"role": "user", "content": parts})
    return out


def tools_openai(tools: list[dict]) -> list[dict]:
    return [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                              "parameters": t.get("input_schema") or {"type": "object", "properties": {}}}}
            for t in tools]


def from_openai(data: dict) -> Reply:
    ch = ((data.get("choices") or [{}])[0]) or {}
    msg = ch.get("message") or {}
    blocks: list[dict] = []
    text = msg.get("content")
    if isinstance(text, list):
        text = " ".join(str(p.get("text") or "") for p in text if isinstance(p, dict))
    if text and str(text).strip():
        blocks.append({"type": "text", "text": str(text).strip()})
    for i, c in enumerate(msg.get("tool_calls") or []):
        fn = c.get("function") or {}
        raw = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (ValueError, TypeError):
            args = {}
        blocks.append({"type": "tool_use", "id": str(c.get("id") or f"call_{i}"), "name": str(fn.get("name") or ""),
                       "input": args if isinstance(args, dict) else {}})
    fin = str(ch.get("finish_reason") or "")
    stop = {"length": "max_tokens", "content_filter": "refusal", "tool_calls": "tool_use"}.get(fin, fin or "end_turn")
    return Reply(content=blocks, stop=stop, model=str(data.get("model") or ""))


async def _post(url: str, key: str, body: dict, timeout: float) -> dict:
    import httpx
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(url, json=body, headers={"Authorization": f"Bearer {key}"})
    if r.status_code >= 400:
        raise QwenError(r.status_code, r.text[:300])
    return r.json()


class QwenError(Exception):
    def __init__(self, code: int, text: str):
        super().__init__(f"Qwen {code}: {text}")
        self.code = code


class CreditLow(QwenError):
    """v0.878 OpenRouter refused for credit even after waiting and asking for less room: the task stops cleanly."""


class BrainSlow(QwenError):
    """v0.879 the AI did not answer a PC step in time, twice: the task stops cleanly instead of hanging for minutes."""


async def think_qwen(model: str, system: str, messages: list[dict], tools: list[dict], max_tokens: int,
                     on_slow=None) -> Reply:
    st = get_settings()
    route = qwen_route()
    if route is None:
        raise QwenError(401, "no OpenRouter key on the server (OPENROUTER_API_KEY)")
    url, key, _ = route
    msgs = to_openai(system, messages)
    claude = str(model).startswith("anthropic/")
    if claude and msgs and msgs[0].get("role") == "system":
        # v0.866 OpenRouter passes Anthropic prompt caching through cache_control: the long PC rules are read cheap
        msgs[0] = {"role": "system", "content": [{"type": "text", "text": str(msgs[0]["content"]),
                                                   "cache_control": {"type": "ephemeral"}}]}
    body: dict[str, Any] = {"model": model, "messages": msgs, "tools": tools_openai(tools), "max_tokens": max_tokens}
    think = "" if claude else str(getattr(st, "pc_qwen_thinking", "") or "").strip().lower()
    if think in ("on", "off"):
        body["reasoning"] = {"enabled": think == "on"}   # OpenRouter's own reasoning switch
    sort = "" if claude else str(getattr(st, "pc_qwen_provider_sort", "") or "").strip().lower()
    if sort in ("latency", "throughput", "price"):
        body["provider"] = {"sort": sort}   # v0.856 PC SPEED: OpenRouter picks the fastest-answering Qwen host
    from ..agent import llm as _llm
    credit_left = len(_llm.CREDIT_WAITS)
    attempt = 0
    while True:
        try:
            data = await _post(url, key, body, float(getattr(st, "pc_brain_timeout_s", 90) or 90))
            break
        except QwenError as e:
            STATS["qwen_errors"] += 1
            if _llm.credit_402(e.code):
                # v0.878 CREDIT ROKE NAHI: 402 = OpenRouter held too much credit for the requests in flight; wait for
                # them and ask for less output room (a PC step needs ~300-800 tokens, not 4000)
                if credit_left > 0:
                    w = _llm.CREDIT_WAITS[len(_llm.CREDIT_WAITS) - credit_left]
                    credit_left -= 1
                    body = _llm.credit_body(body, floor=800) or body
                    STATS["credit_holds"] = STATS.get("credit_holds", 0) + 1
                    log.warning("pc brain 402 credit hold: waiting %.0fs, asking again with max_tokens %s", w,
                                body.get("max_tokens"))
                    await asyncio.sleep(w)
                    continue
                raise CreditLow(402, str(e)[:200]) from e
            attempt += 1
            if e.code in (408, 429, 500, 502, 503, 504) and attempt < 3:
                await asyncio.sleep(2 + 2 * attempt)
                continue
            raise
        except Exception as e:
            STATS["qwen_errors"] += 1
            import httpx
            if isinstance(e, httpx.TimeoutException):
                # v0.879 TEZ YA SAAF: a step the AI does not answer in time is said at once and tried ONCE more - never
                # minutes of silence (her 02:59 Aadhaar step hung 3.5 min: 90 s x 3 quiet tries)
                STATS["slow"] = STATS.get("slow", 0) + 1
                attempt += 1
                if attempt < 2:
                    log.warning("pc brain step not answered in time; telling her and trying once more")
                    if on_slow:
                        try:
                            on_slow()
                        except Exception:
                            pass
                    continue
                raise BrainSlow(504, "the AI did not answer this PC step in time (twice)") from e
            attempt += 1
            if attempt < 3:
                await asyncio.sleep(2 * attempt)
                continue
            raise
    u = data.get("usage") or {}
    cached = int(((u.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0)
    try:
        from .. import usage
        usage.record(model, tok_in=max(0, int(u.get("prompt_tokens") or 0) - cached),
                     tok_out=int(u.get("completion_tokens") or 0), cache_read=cached)
    except Exception:
        pass
    rep = from_openai(data)
    rep.model = rep.model or model
    return rep


def _tell_slow(op) -> None:
    """v0.879 one spoken line on her live call (and the card) when the AI is slow to answer a PC step."""
    try:
        op.action = "AI is slow to answer, trying again"
        from . import operator as _op
        _op._inject(op, "(PC update - say it in a few natural words: «AI thoda slow hai, dobara try kar raha hoon.»)")
        _op._event(op)
    except Exception:
        pass


async def think(op, client, messages: list[dict], params: dict, retry) -> Reply:
    """One step of the PC loop on the brain this task runs on. `retry` = operator._think_retry (the Claude path's
    own retries + history sanitising)."""
    brain, model = getattr(op, "brain", "") or "sonnet", getattr(op, "brain_model", "") or params.get("model")
    helped = False
    if brain == "qwen27":
        from . import rescue
        r_ = rescue.rescue_active(op)       # v0.867 stuck: a few steps on the strong model, then back to the cheap one
        if r_:
            brain, model, helped = r_[0], r_[1], True
    try:
        from . import rescue as _rs
        _rs.charge(op, brain)               # v0.867 the daily rupee estimate
    except Exception:
        pass
    t0 = time.monotonic()
    if brain in ("qwen", "qwen27", "sonnet-or"):
        STATS[brain if brain in ("qwen", "qwen27") else "sonnet"] += 1
        rep = await think_qwen(model, params.get("system", ""), messages, params.get("tools") or [],
                               int(params.get("max_tokens") or 1500), on_slow=lambda: _tell_slow(op))
    else:
        STATS["sonnet"] += 1
        from .. import usage, glmdoor
        a = usage.ONE_MODEL_BYPASS.set(True)    # the PC loop runs on the model it names, never the Haiku rewrite
        b = glmdoor.CLAUDE_ONLY.set(True)       # and never the GLM door (GLM-Flash cannot be trusted with a screen)
        try:
            resp = await retry(op, client, messages, {**params, "model": model})
        finally:
            glmdoor.CLAUDE_ONLY.reset(b)
            usage.ONE_MODEL_BYPASS.reset(a)
        rep = Reply(content=[x.model_dump(exclude_none=True) if hasattr(x, "model_dump") else x for x in resp.content],
                    stop=str(getattr(resp, "stop_reason", "") or ""), model=str(getattr(resp, "model", "") or model))
    log.info("pc brain %s %s step %d %.1fs stop=%s%s", brain, model, getattr(op, "step", 0), time.monotonic() - t0, rep.stop,
             " (rescue)" if helped else "")
    return rep
