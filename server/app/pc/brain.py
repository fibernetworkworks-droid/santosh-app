"""v0.851 PC BRAIN (owner: "FOR PC WE CURRENTLY CHOOSE 2 MODELS QWEN 3.8 AND SONET 5.5 --- WILL TEST IT FIRST ---
WILL START WITH QWEN"): the model that SEES her screen and picks the next click, chosen for the PC loop alone.

Two brains, one shape. The operator loop keeps speaking Anthropic's message format (text / image / tool_use /
tool_result blocks); this module turns one step into either
  - "qwen":   Alibaba Model Studio's OpenAI-compatible endpoint (QWEN_API_KEY + QWEN_BASE_URL in the VPS .env only),
              model `pc_qwen_model` (qwen3.8-max). Screenshots ride as image_url data URIs; a tool result's
              screenshot is sent in the user message right after the tool messages (OpenAI tool messages are text).
  - "sonnet": Claude `pc_sonnet_model` (claude-sonnet-5-5) through the SDK, with the "everything on Haiku" rewrite
              (usage.one_model) and the GLM door both standing aside for this call - so the PC loop gets the model
              it names, not Haiku or GLM-Flash.
and hands back an object with `.content` (Anthropic-shaped dicts), `.stop` and `.model`.

No Qwen key = the step runs on Sonnet and the task says so once (op.brain_note) - never a silent swap.
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

BRAINS = ("qwen", "sonnet")
STATS: dict[str, int] = {"qwen": 0, "sonnet": 0, "fallback": 0, "qwen_errors": 0}


@dataclass
class Reply:
    content: list[dict] = field(default_factory=list)
    stop: str = ""          # end_turn / tool_use / max_tokens / refusal (Anthropic words, Qwen's mapped onto them)
    model: str = ""


def norm(name: str) -> str:
    n = str(name or "").strip().lower()
    if n.startswith("qwen"):
        return "qwen"
    if n.startswith(("sonnet", "claude")):
        return "sonnet"
    return ""


OPENROUTER = "https://openrouter.ai/api/v1"


def qwen_route() -> tuple[str, str, str] | None:
    """v0.852 (url, key, model) for Qwen: Alibaba Model Studio when QWEN_API_KEY is set, else OpenRouter with the
    OpenRouter key the server already has (qwen/qwen3.8-max-0902 there - reads screenshots, calls tools). None = no key."""
    st = get_settings()
    key = str(getattr(st, "qwen_api_key", "") or "").strip()
    if key:
        base = str(getattr(st, "qwen_base_url", "") or "").rstrip("/") or "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
        model = str(getattr(st, "pc_qwen_model", "") or "qwen3.8-max")
        if "openrouter.ai" in base and "/" not in model:
            model = str(getattr(st, "pc_qwen_openrouter_model", "") or "qwen/qwen3.8-max-0902")
        return base + "/chat/completions", key, model
    try:
        from ..agent.providers import key_of
        okey = key_of("openrouter")
    except Exception:
        okey = ""
    if okey:
        return (OPENROUTER + "/chat/completions", okey,
                str(getattr(st, "pc_qwen_openrouter_model", "") or "qwen/qwen3.8-max-0902"))
    return None


def choose(want: str = "") -> tuple[str, str, str]:
    """(brain, model, note). `want` = this task's pick ('' = the server's pc_model). A Qwen pick with no key at all
    (neither QWEN_API_KEY nor an OpenRouter key) runs on Sonnet and says why in `note`."""
    st = get_settings()
    brain = norm(want) or norm(getattr(st, "pc_model", "")) or "sonnet"
    route = qwen_route() if brain == "qwen" else None
    if brain == "qwen" and route is None:
        STATS["fallback"] += 1
        return ("sonnet", str(getattr(st, "pc_sonnet_model", "") or "claude-sonnet-5-5"),
                "No Qwen key (QWEN_API_KEY or OPENROUTER_API_KEY) is on the server, so this PC task ran on Sonnet 5.5.")
    if brain == "qwen":
        return "qwen", route[2], ""
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


async def think_qwen(model: str, system: str, messages: list[dict], tools: list[dict], max_tokens: int) -> Reply:
    st = get_settings()
    route = qwen_route()
    if route is None:
        raise QwenError(401, "no Qwen key on the server (QWEN_API_KEY or OPENROUTER_API_KEY)")
    url, key, _ = route
    body: dict[str, Any] = {"model": model, "messages": to_openai(system, messages), "tools": tools_openai(tools),
                            "max_tokens": max_tokens}
    think = str(getattr(st, "pc_qwen_thinking", "") or "").strip().lower()
    if think in ("on", "off"):
        body["enable_thinking"] = think == "on"
    if "openrouter.ai" in url:
        body.pop("enable_thinking", None)      # an Alibaba field; OpenRouter has its own reasoning switch
        if think in ("on", "off"):
            body["reasoning"] = {"enabled": think == "on"}
    for attempt in range(3):
        try:
            data = await _post(url, key, body, float(getattr(st, "pc_brain_timeout_s", 90) or 90))
            break
        except QwenError as e:
            STATS["qwen_errors"] += 1
            if e.code in (408, 429, 500, 502, 503, 504) and attempt < 2:
                await asyncio.sleep(2 + 2 * attempt)
                continue
            raise
        except Exception:
            STATS["qwen_errors"] += 1
            if attempt < 2:
                await asyncio.sleep(2 + 2 * attempt)
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


async def think(op, client, messages: list[dict], params: dict, retry) -> Reply:
    """One step of the PC loop on the brain this task runs on. `retry` = operator._think_retry (the Claude path's
    own retries + history sanitising)."""
    brain, model = getattr(op, "brain", "") or "sonnet", getattr(op, "brain_model", "") or params.get("model")
    t0 = time.monotonic()
    if brain == "qwen":
        STATS["qwen"] += 1
        rep = await think_qwen(model, params.get("system", ""), messages, params.get("tools") or [],
                               int(params.get("max_tokens") or 4000))
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
    log.info("pc brain %s %s step %d %.1fs stop=%s", brain, model, getattr(op, "step", 0), time.monotonic() - t0, rep.stop)
    return rep
