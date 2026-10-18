"""Which brain answers a chat turn.

Santosh keeps every conversation in Anthropic's message format (text / tool_use / tool_result blocks).
For a low-cost brain, any OpenAI-compatible chat API can be used instead: Z.ai GLM by default, or a
self-hosted GLM (vLLM / SGLang) in an Indian data centre — only GLM_BASE_URL changes.

Routing (CHAT_LLM):
  auto    GLM when GLM_API_KEY is set, otherwise Claude
  glm     always GLM (Claude only as fallback when GLM is down)
  claude  always Claude
Claude is also used when a turn carries images/documents, or after GLM fails, so a GLM outage never
leaves the user without an answer. Safety never depends on the model: payments and messages stay frozen
server-side until the user approves them in the app.
"""
from __future__ import annotations

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


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=httpx.Timeout(90, connect=15))
    return _http


def glm_ready() -> bool:
    return bool(get_settings().glm_api_key)


def choose(messages: list[dict]) -> str:
    """'glm' or 'claude' for this turn."""
    st = get_settings()
    mode = (st.chat_llm or "auto").lower()
    if mode == "claude" or not glm_ready():
        return "claude"
    if _has_media(messages[-1:]) and st.anthropic_api_key:
        return "claude"          # pictures and PDFs go to the model that reads them well
    return "glm"


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
            t = _text_of(extra)
            if t:
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
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
            if not isinstance(args, dict):
                args = {}
        except json.JSONDecodeError:
            args = {}
        tid = re.sub(r"[^a-zA-Z0-9_-]", "_", tc.get("id") or "") or f"call_{uuid.uuid4().hex[:12]}"
        blocks.append({"type": "tool_use", "id": tid,
                       "name": fn.get("name", ""), "input": args})
    stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
    return blocks, stop


class LLMError(RuntimeError):
    pass


async def glm_create(system: str, tools: list[dict], messages: list[dict], max_tokens: int) -> tuple[list[dict], str, dict]:
    st = get_settings()
    msgs, fns = to_openai(system, tools, messages)
    body: dict = {"model": st.glm_model, "messages": msgs, "max_tokens": max_tokens, "temperature": st.glm_temperature}
    if fns:
        body["tools"] = fns
        body["tool_choice"] = "auto"
    if st.glm_thinking in ("enabled", "disabled"):
        body["thinking"] = {"type": st.glm_thinking}   # Z.ai extension; self-hosted servers ignore it
    url = st.glm_base_url.rstrip("/") + "/chat/completions"
    try:
        r = await _client().post(url, json=body, headers={"Authorization": f"Bearer {st.glm_api_key}"})
    except httpx.HTTPError as e:
        raise LLMError(f"GLM not reachable: {e}") from e
    if r.status_code >= 400:
        raise LLMError(f"GLM error {r.status_code}: {r.text[:300]}")
    data = r.json()
    blocks, stop = from_openai(data)
    if not blocks:
        raise LLMError("GLM returned an empty answer")
    return blocks, stop, data.get("usage") or {}
