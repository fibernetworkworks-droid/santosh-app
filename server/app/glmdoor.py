"""SAB GLM - every Claude call in Hoola answered by GLM (owner: "NOW LETS USE GLM 5.3 FLASH FOR ALL USE - AS NVIDIA
PROVIDING FREE API").

Hoola talks to Claude through ONE door: the Anthropic SDK's Messages.create / .stream, wrapped once in
`usage.install()` (that is where SAB HAIKU already rewrites the model). With `claude_all_glm` switched on and a GLM key
set, that door answers the call from the OpenAI-compatible GLM brain instead - NVIDIA's free hosted
`z-ai/glm-5.3-flash` at https://integrate.api.nvidia.com/v1 by default - and hands the caller back a REAL
`anthropic.types.Message`, so every engine (chat fallback, reviewers, compaction, summaries, site builder, game desk,
coder, research ...) keeps working without knowing.

Rules:
- Pictures / PDFs in the call go to real Claude when its key is set (the chat already does this, llm.choose).
- If GLM fails (down, 429 rate limit, refused) the SAME call goes to real Claude when `claude_all_glm_fallback` is on and
  an Anthropic key is set - she is never left without an answer. With no Claude key the GLM error is raised as is.
- Gemini Live (the call's voice) is untouched: it is a voice engine, not a text brain.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import httpx

log = logging.getLogger("santosh.glmdoor")
STATS: dict[str, int] = {"glm": 0, "fallback_claude": 0, "media_to_claude": 0, "failed": 0}


def _settings():
    from .config import get_settings
    return get_settings()


def brain() -> str:
    """Which OpenAI-style brain the door uses: OmniRoute when it is set up (owner: "check omniroute" -> GO - one gateway
    with its own provider fallbacks, official API keys only), else the GLM endpoint. `claude_all_brain` can pin one."""
    try:
        st = _settings()
        want = str(getattr(st, "claude_all_brain", "") or "").lower()
        if want in ("glm", "omniroute"):
            return want
        return "omniroute" if st.omniroute_url else "glm"
    except Exception:
        return "glm"


def _ready(b: str) -> bool:
    st = _settings()
    return bool(st.omniroute_url) if b == "omniroute" else bool(st.glm_api_key)


def active() -> bool:
    try:
        st = _settings()
        if not getattr(st, "claude_all_glm", False):
            return False
        b = brain()
        if not _ready(b):
            return False
        from .agent import llm
        return not llm.brain_paused(b)       # the safety switch: a hung brain is skipped for a while, Claude answers
    except Exception:
        return False


def _claude_ok() -> bool:
    try:
        st = _settings()
        return bool(getattr(st, "claude_all_glm_fallback", True) and st.anthropic_api_key)
    except Exception:
        return False


def _system_text(system: Any) -> str:
    if isinstance(system, str):
        return system
    out = []
    for b in system or []:
        if isinstance(b, dict) and b.get("type") == "text":
            out.append(str(b.get("text") or ""))
        elif getattr(b, "text", None):
            out.append(str(b.text))
    return "\n\n".join(out)


def _plain(m: Any) -> Any:
    """SDK block objects (a previous answer handed back) -> plain dicts."""
    if hasattr(m, "model_dump"):
        return m.model_dump()
    if isinstance(m, dict):
        return {k: _plain(v) for k, v in m.items()}
    if isinstance(m, list):
        return [_plain(x) for x in m]
    return m


def has_media(messages: list) -> bool:
    """A call GLM cannot read well: PDFs always; pictures only when the GLM endpoint is not NVIDIA (which reads them)."""
    try:
        from .agent import llm
        pics_ok = llm.is_nvidia() and brain() == "glm"
    except Exception:
        pics_ok = False
    kinds = ("document",) if pics_ok else ("image", "document")
    for m in messages or []:
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") in kinds for b in c):
            return True
    return False


def _tool_choice(tc: Any) -> Any:
    if not isinstance(tc, dict):
        return "auto"
    t = tc.get("type")
    if t == "tool" and tc.get("name"):
        return {"type": "function", "function": {"name": tc["name"]}}
    if t == "any":
        return "required"
    if t == "none":
        return "none"
    return "auto"


def _expand_refs(messages: list) -> tuple[list, set]:
    """tool_search answers with tool_reference blocks that Claude's API expands; GLM cannot. Each becomes a text line
    naming the loaded tool, and the names come back so those tools join GLM's tool list."""
    found: set = set()
    for m in messages:
        c = m.get("content") if isinstance(m, dict) else None
        if not isinstance(c, list):
            continue
        for b in c:
            if not (isinstance(b, dict) and b.get("type") == "tool_result" and isinstance(b.get("content"), list)):
                continue
            inner = []
            for x in b["content"]:
                if isinstance(x, dict) and x.get("type") == "tool_reference" and x.get("tool_name"):
                    found.add(x["tool_name"])
                    inner.append({"type": "text", "text": f"Tool loaded, you can call it now: {x['tool_name']}"})
                else:
                    inner.append(x)
            b["content"] = inner
    return messages, found


def build(kw: dict) -> tuple[str, dict, dict, str]:
    """(url, headers, body, label) for one Anthropic-style call."""
    from .agent import llm
    messages, found = _expand_refs(_plain(kw.get("messages") or []))
    # v0.702: Claude's tool search sends ~650 tools with only ~60 in view (defer_loading: true for the rest); GLM has
    # no such switch, so every deferred tool used to ride in FULL - ~70k tokens a step, slow, timing out. GLM now gets
    # what Claude sees: the tools in view + the ones tool_search has loaded in this conversation.
    tools = [{k: v for k, v in t.items() if k != "defer_loading"} for t in (_plain(kw.get("tools") or []))
             if isinstance(t, dict) and t.get("name") and t.get("type") in (None, "custom")   # no GLM twin for server tools
             and (not t.get("defer_loading") or t.get("name") in found)]
    msgs, fns = llm.to_openai(_system_text(kw.get("system")), tools, messages)
    b = brain()
    url, model, label, headers, extra = llm._target(b)
    mt = int(kw.get("max_tokens") or 1024)
    body: dict = {"model": model, "messages": msgs,
                  "max_tokens": llm.room(mt) if b == "glm" else mt,
                  "temperature": float(kw.get("temperature", _settings().glm_temperature)), **extra}
    if fns:
        body["tools"] = fns
        body["tool_choice"] = _tool_choice(kw.get("tool_choice"))
    return url, headers, body, label


def to_message(data: dict, model: str) -> Any:
    """An OpenAI chat answer -> a real anthropic.types.Message."""
    from anthropic.types import Message, TextBlock, ToolUseBlock, Usage
    from .agent import llm
    blocks, stop = llm.from_openai(data)
    content = []
    for b in blocks:
        if b["type"] == "text":
            content.append(TextBlock(type="text", text=b["text"]))
        elif b["type"] == "tool_use":
            content.append(ToolUseBlock(type="tool_use", id=b["id"], name=b["name"], input=b["input"]))
    if not content:
        content.append(TextBlock(type="text", text=""))
    u = data.get("usage") or {}
    return Message(id=str(data.get("id") or f"msg_glm_{uuid.uuid4().hex[:16]}"), type="message", role="assistant",
                   model=str(data.get("model") or model), content=content, stop_reason=stop, stop_sequence=None,
                   usage=Usage(input_tokens=int(u.get("prompt_tokens") or 0),
                               output_tokens=int(u.get("completion_tokens") or 0)))


def _count(data: dict, model: str) -> None:
    try:
        from . import usage as _usage
        _usage.from_openai(data.get("model") or model, dict(data.get("usage") or {}))
    except Exception:
        pass


async def acreate(kw: dict) -> Any:
    from .agent import llm
    try:
        msg = await _acreate(kw)
    except Exception:
        llm.brain_result(brain(), False)
        raise
    llm.brain_result(brain(), True)
    return msg


async def _acreate(kw: dict) -> Any:
    from .agent import llm
    url, headers, body, label = build(kw)
    r = await llm._post_with_retry(url, body, headers, label)
    try:
        data = r.json()
    except ValueError as e:
        raise llm.LLMError(f"{label} sent a broken answer: {e}") from e
    _count(data, body["model"])
    msg = to_message(data, body["model"])
    if not any((getattr(b, "text", "") or getattr(b, "name", "")) for b in msg.content):
        raise llm.LLMError(f"{label} returned an empty answer")
    STATS["glm"] += 1
    return msg


def create_sync(kw: dict) -> Any:
    from .agent import llm
    try:
        msg = _create_sync(kw)
    except Exception:
        llm.brain_result(brain(), False)
        raise
    llm.brain_result(brain(), True)
    return msg


def _create_sync(kw: dict) -> Any:
    from .agent import llm
    url, headers, body, label = build(kw)
    with httpx.Client(**(llm._brain_timeout(label) or {"timeout": llm._glm_timeout()})) as c:
        r = c.post(url, json=body, headers=headers)
        if r.status_code >= 400 and body.pop("reasoning_effort", None) is not None:
            body.pop("chat_template_kwargs", None)       # an endpoint that does not know the reasoning fields
            r = c.post(url, json=body, headers=headers)
    if r.status_code >= 400:
        raise llm.LLMError(f"{label} error {r.status_code}: {r.text[:300]}")
    data = r.json()
    _count(data, body["model"])
    msg = to_message(data, body["model"])
    if not any((getattr(b, "text", "") or getattr(b, "name", "")) for b in msg.content):
        raise llm.LLMError(f"{label} returned an empty answer")
    STATS["glm"] += 1
    return msg


# ---------------------------------------------------------------- streams
class _Stream:
    """What the SDK's `messages.stream(...)` gives: an async context manager whose final message is the GLM answer.
    Callers that read events see the whole text as one delta; callers that read get_final_message() get it whole."""

    def __init__(self, kw: dict, fallback):
        self.kw, self.fallback, self._msg, self._inner = kw, fallback, None, None

    async def _get(self):
        if self._msg is None:
            try:
                self._msg = await acreate(self.kw)
            except Exception as e:
                if self.fallback is None or not _claude_ok():
                    STATS["failed"] += 1
                    raise
                log.warning("GLM door failed (%s) - this streamed call goes to Claude", str(e)[:200])
                STATS["fallback_claude"] += 1
                self._inner = self.fallback()
                s = await self._inner.__aenter__()
                self._msg = await s.get_final_message()
        return self._msg

    async def __aenter__(self):
        await self._get()
        return self

    async def __aexit__(self, *exc):
        if self._inner is not None:
            await self._inner.__aexit__(*exc)
        return False

    async def get_final_message(self):
        return await self._get()

    @property
    def text_stream(self):
        async def gen():
            m = await self._get()
            t = "".join(getattr(b, "text", "") or "" for b in m.content)
            if t:
                yield t
        return gen()

    def __aiter__(self):
        async def gen():
            from types import SimpleNamespace
            m = await self._get()
            t = "".join(getattr(b, "text", "") or "" for b in m.content)
            if t:
                yield SimpleNamespace(type="content_block_delta", index=0,
                                      delta=SimpleNamespace(type="text_delta", text=t))
            yield SimpleNamespace(type="message_stop")
        return gen()


class _SyncStream:
    """The sync twin (site/ai.py builds sections with `with client.messages.stream(...)`)."""

    def __init__(self, kw: dict, fallback):
        self.kw, self.fallback, self._msg, self._inner = kw, fallback, None, None

    def _get(self):
        if self._msg is None:
            try:
                self._msg = create_sync(self.kw)
            except Exception as e:
                if self.fallback is None or not _claude_ok():
                    STATS["failed"] += 1
                    raise
                log.warning("GLM door failed (%s) - this streamed call goes to Claude", str(e)[:200])
                STATS["fallback_claude"] += 1
                self._inner = self.fallback()
                self._msg = self._inner.__enter__().get_final_message()
        return self._msg

    def __enter__(self):
        self._get()
        return self

    def __exit__(self, *exc):
        if self._inner is not None:
            self._inner.__exit__(*exc)
        return False

    def get_final_message(self):
        return self._get()

    @property
    def text_stream(self):
        m = self._get()
        t = "".join(getattr(b, "text", "") or "" for b in m.content)
        return iter([t] if t else [])

    def __iter__(self):
        from types import SimpleNamespace
        m = self._get()
        t = "".join(getattr(b, "text", "") or "" for b in m.content)
        out = [SimpleNamespace(type="content_block_delta", index=0, delta=SimpleNamespace(type="text_delta", text=t))] \
            if t else []
        return iter(out + [SimpleNamespace(type="message_stop")])


def status() -> dict:
    st = _settings()
    from .agent import llm
    b = brain()
    return {"on": active(), "brain": b, "paused": llm.brain_paused(b), "breaker": dict(llm.BREAKERS.get(b, {})),
            "model": st.omniroute_model if b == "omniroute" else st.glm_model,
            "base_url": st.omniroute_url if b == "omniroute" else st.glm_base_url,
            "claude_fallback": _claude_ok(), **STATS, "key_set": bool(st.glm_api_key), "omniroute_set": bool(st.omniroute_url)}


__all__ = ["active", "acreate", "create_sync", "has_media", "status", "_Stream", "json"]


async def _check() -> int:
    """`python -m app.glmdoor check`: one tiny text call + one tool call through the SAME door every call uses."""
    import time
    st = _settings()
    b = brain()
    where = (f"OmniRoute {st.omniroute_url} model {st.omniroute_model}" if b == "omniroute"
             else f"GLM endpoint {st.glm_base_url} model {st.glm_model} key {'set' if st.glm_api_key else 'NOT SET'}")
    print(f"{where}; SAB GLM {'ON' if active() else 'off'}; Claude fallback {'yes' if _claude_ok() else 'no'}")
    if not _ready(b):
        print("GADBAD: " + ("OMNIROUTE_URL is empty" if b == "omniroute" else
                            "GLM_API_KEY is empty (make one at your provider, put it in .env)"))
        return 1
    rc = 0
    t = time.monotonic()
    try:
        m = await acreate({"model": "check", "max_tokens": 64, "system": "Answer in one word.",
                           "messages": [{"role": "user", "content": "Reply with the word OK."}]})
        txt = "".join(getattr(b, "text", "") or "" for b in m.content).strip()
        print(f"text call: {time.monotonic() - t:.1f} s -> {txt[:80]!r} ({m.usage.input_tokens} in / "
              f"{m.usage.output_tokens} out)")
    except Exception as e:
        print(f"GADBAD text call: {str(e)[:400]}")
        rc = 1
    t = time.monotonic()
    try:
        m = await acreate({"model": "check", "max_tokens": 200, "system": "Use the tool.",
                           "tools": [{"name": "get_weather", "description": "Weather for a city",
                                      "input_schema": {"type": "object", "properties": {"city": {"type": "string"}},
                                                       "required": ["city"]}}],
                           "messages": [{"role": "user", "content": "Pune ka mausam batao"}]})
        calls = [(b.name, b.input) for b in m.content if getattr(b, "type", "") == "tool_use"]
        print(f"tool call: {time.monotonic() - t:.1f} s -> {calls or 'NO tool call'} (stop {m.stop_reason})")
        if not calls:
            rc = 1
    except Exception as e:
        print(f"GADBAD tool call: {str(e)[:400]}")
        rc = 1
    print("PAKKA: GLM answers through the door" if rc == 0 else "GADBAD: see the lines above")
    return rc


if __name__ == "__main__":
    import asyncio
    import sys
    if sys.argv[1:2] == ["check"]:
        raise SystemExit(asyncio.run(_check()))
    print(json.dumps(status(), indent=2))
