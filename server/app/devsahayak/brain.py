"""v0.784 HOOLA CODE - one Claude call for every Hoola Code loop (the working-copy engine, the old 8-tool loop, the plan
and review passes). Step 1 of the owner's "GO STEP 1 AND 2 --- 2 SESSIONS, USE CLAUDE".

What every coding call now gets, and why:
- CLAUDE, ALWAYS (`dev_claude`): the owner's server routes every Claude call to GLM (SAB GLM, `claude_all_glm`) and may
  pin one model (`claude_one_model`). For Hoola Code she decided "USE CLAUDE", so a coding call stands both doors
  aside (`glmdoor.CLAUDE_ONLY` + `usage.ONE_MODEL_BYPASS`, the website architect's v0.710 pattern). Off = old behaviour.
- THINKING (`dev_think`): adaptive thinking, Claude decides how much. A model / account that refuses the field is
  asked again without it and the refusal is remembered for this process.
- PROMPT CACHING: the system prompt, the tool list and the conversation so far are marked cacheable, so step 30 of a
  session does not pay full price for steps 1-29 again (before v0.784 every step resent everything at full price).
- OLD TOOL OUTPUT TRIMMED (`trim`): past a budget, all but the newest tool results are replaced by a one-line marker
  ("run the tool again if you need it") - Anthropic's own context-editing idea. Done in place and in one go, so the
  cached prefix changes rarely.

v0.926 HOOLA CODE ON QWEN (owner: "27B FOR CODING ALSO"): with `dev_brain` "qwen" (the default) every one of those
calls goes to Qwen on OpenRouter (`dev_qwen_model`, qwen/qwen3.8-27b) on its OWN request - its own clock
(`dev_qwen_timeout_s`), its own retries, never the chat's GLM door, so a slow coding step can never pause anyone's chat.
Her effort becomes Qwen's reasoning effort (reasoning text kept out of the answer and out of the history, so a session
can move back to Claude at any time). No OpenRouter key = Claude, said in the log. A failed Qwen call is never quietly
moved to Claude (`dev_qwen_fallback_claude` off).

Tests replace CLIENT (a fake with .messages.create) and QWEN_POST (a fake that answers one OpenRouter request)."""
from __future__ import annotations

import contextlib
import copy
import logging
import threading
from typing import Any

log = logging.getLogger("santosh.devsahayak.brain")

CLIENT: Any = None                      # tests: a fake with .messages.create(**kw)
QWEN_POST: Any = None                   # tests: a fake(url, body, headers, timeout) -> the OpenRouter JSON answer
STATE = {"think_refused": False, "effort_refused": False, "calls": 0, "cleared": 0, "qwen_calls": 0, "qwen_failed": 0}
CLEARED = "[older tool output cleared to keep the session small - run the tool again if you need it]"
PICK = threading.local()                # model / effort chosen for THIS session (the composer), set by the caller


def _settings():
    from ..config import get_settings
    return get_settings()


def _or_key() -> str:
    try:
        from ..agent import providers as _pv
        return _pv.key_of("openrouter")
    except Exception:
        return ""


def brain_name() -> str:
    """Which brain answers Hoola Code: "qwen" (OpenRouter) or "claude"."""
    st = _settings()
    if str(getattr(st, "dev_brain", "claude") or "claude").strip().lower() != "qwen":
        return "claude"
    if QWEN_POST is not None or _or_key():
        return "qwen"
    if not STATE.get("no_key_said"):
        STATE["no_key_said"] = True
        log.warning("Hoola Code is set to Qwen but the server has no OpenRouter key - answering on Claude")
    return "claude"


def qwen_model() -> str:
    """The Qwen model: a qwen/ model she picked for this session, else dev_qwen_model (a Claude pick - the hint and
    memory callers ask for Haiku - means nothing on the Qwen brain)."""
    picked = str(getattr(PICK, "model", "") or "")
    if picked.startswith("qwen/"):
        return picked
    return str(getattr(_settings(), "dev_qwen_model", "") or "qwen/qwen3.8-27b")


def model_for() -> str:
    st = _settings()
    if brain_name() == "qwen":
        return qwen_model()
    return (getattr(PICK, "model", "") or getattr(st, "dev_loop_model", "") or getattr(st, "site_model", "")
            or st.anthropic_model)


@contextlib.contextmanager
def claude_only():
    """Stand the GLM door and the one-model rule aside for a Hoola Code call (only when `dev_claude` is on)."""
    if not bool(getattr(_settings(), "dev_claude", True)):
        yield
        return
    from .. import glmdoor
    from .. import usage as U
    a, b = glmdoor.CLAUDE_ONLY.set(True), U.ONE_MODEL_BYPASS.set(True)
    try:
        yield
    finally:
        glmdoor.CLAUDE_ONLY.reset(a)
        U.ONE_MODEL_BYPASS.reset(b)


def _client():
    if CLIENT is not None:
        return CLIENT
    st = _settings()
    if not st.anthropic_api_key:
        raise RuntimeError("no ANTHROPIC_API_KEY")
    import anthropic
    return anthropic.Anthropic(api_key=st.anthropic_api_key)


def _cacheable(system: str, tools: list[dict], messages: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Copies with cache breakpoints on the system prompt, the last tool and the last message (3 of the 4 allowed).
    The stored history is never changed."""
    sys_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    tl = [dict(t) for t in tools]
    if tl:
        tl[-1] = {**tl[-1], "cache_control": {"type": "ephemeral"}}
    msgs = list(messages)
    if msgs:
        last = copy.deepcopy(msgs[-1])
        content = last.get("content")
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        if isinstance(content, list) and content:
            for i in range(len(content) - 1, -1, -1):
                if isinstance(content[i], dict) and content[i].get("type") in ("text", "tool_result", "image"):
                    content[i] = {**content[i], "cache_control": {"type": "ephemeral"}}
                    break
            last["content"] = content
        msgs[-1] = last
    return sys_blocks, tl, msgs


def _refused(e: Exception, word: str) -> bool:
    m = str(e).lower()
    return word in m and any(w in m for w in ("400", "invalid", "not support", "unsupported", "unexpected", "extra"))


def call(system: str, messages: list[dict], tools: list[dict], max_tokens: int = 16000,
         think: bool | None = None) -> tuple[list[dict], str]:
    """One model step with tools. Returns (content blocks incl. thinking, stop_reason)."""
    if brain_name() == "qwen":
        try:
            return _qwen_call(system, messages, tools, max_tokens, think)
        except Exception as e:
            STATE["qwen_failed"] += 1
            if not (bool(getattr(_settings(), "dev_qwen_fallback_claude", False)) and _settings().anthropic_api_key):
                raise
            log.warning("Hoola Code Qwen call failed (%s) - asking Claude once (dev_qwen_fallback_claude)", str(e)[:160])
            return _claude_call(system, messages, tools, max_tokens, think)
    return _claude_call(system, messages, tools, max_tokens, think)


EFFORT_TO_REASONING = {"low": "low", "medium": "medium", "high": "high", "xhigh": "high", "max": "high"}
ROOM = {"low": 2048, "medium": 4096, "high": 8192}       # reasoning tokens counted inside max_tokens on OpenRouter


class QwenError(RuntimeError):
    pass


def _qwen_post(url: str, body: dict, headers: dict, timeout: float) -> dict:
    if QWEN_POST is not None:
        return QWEN_POST(url, body, headers, timeout)
    import httpx
    with httpx.Client(timeout=timeout) as c:
        r = c.post(url, json=body, headers=headers)
    if r.status_code >= 400:
        from ..agent import llm
        line = (" | " + llm.CREDIT_LOW_LINE) if r.status_code == 402 else ""
        raise QwenError(f"OpenRouter answered {r.status_code}: {r.text[:300]}{line}")
    return r.json()


def _qwen_call(system: str, messages: list[dict], tools: list[dict], max_tokens: int,
               think: bool | None) -> tuple[list[dict], str]:
    """One Hoola Code step on Qwen through OpenRouter, answered in the same block shapes a Claude call returns."""
    import time
    from ..agent import llm
    st = _settings()
    model = qwen_model()
    msgs, fns = llm.to_openai(system, [t for t in tools if isinstance(t, dict) and t.get("name")], messages)
    want_think = bool(getattr(st, "dev_think", True)) if think is None else think
    effort = getattr(PICK, "effort", "") or str(getattr(st, "dev_loop_effort", "high") or "high")
    level = EFFORT_TO_REASONING.get(effort.lower(), "high") if want_think else "low"
    body: dict[str, Any] = {"model": model, "messages": msgs, "max_tokens": int(max_tokens) + ROOM[level],
                            "temperature": 0.2, "reasoning": {"effort": level, "exclude": True},
                            "provider": {"require_parameters": True}}
    if fns:
        body["tools"] = fns
        body["tool_choice"] = "auto"
    headers = {"Authorization": f"Bearer {_or_key()}", "X-Title": "Hoola Code"}
    url = "https://openrouter.ai/api/v1/chat/completions"
    timeout = float(getattr(st, "dev_qwen_timeout_s", 180) or 180)
    last: Exception | None = None
    for i in range(3):
        if i:
            time.sleep(3 * i)
        t0 = time.time()
        try:
            data = _qwen_post(url, body, headers, timeout)
        except QwenError as e:
            last = e
            m = str(e)
            log.warning("hoola code qwen %s try %d failed %.1fs: %s", model, i + 1, time.time() - t0, m[:240])
            if any(f" {c}:" in m for c in ("400", "401", "402", "403", "404")):
                raise                                         # a refused request is not fixed by asking again
            continue
        except Exception as e:                                # timeout / network: one more try
            last = e
            log.warning("hoola code qwen %s try %d failed %.1fs: %s %s", model, i + 1, time.time() - t0,
                        e.__class__.__name__, str(e)[:200])
            continue
        if data.get("error"):
            last = QwenError(f"OpenRouter error: {str(data['error'])[:300]}")
            continue
        blocks, stop = llm.from_openai(data)
        if not blocks:
            last = QwenError("Qwen sent an empty answer")
            continue
        u = dict(data.get("usage") or {})
        log.info("hoola code qwen %s %.1fs effort=%s in=%s out=%s tools=%d calls=%d stop=%s", model, time.time() - t0,
                 level, u.get("prompt_tokens"), u.get("completion_tokens"), len(fns),
                 sum(1 for b in blocks if b.get("type") == "tool_use"), stop)
        STATE["calls"] += 1
        STATE["qwen_calls"] += 1
        try:
            from .. import usage
            usage.from_openai(model, dict(data.get("usage") or {}))
        except Exception:
            pass
        return blocks, stop
    raise QwenError(f"Qwen ({model}) did not answer: {last}")


def _claude_call(system: str, messages: list[dict], tools: list[dict], max_tokens: int,
                 think: bool | None) -> tuple[list[dict], str]:
    st = _settings()
    model = model_for()
    sys_blocks, tl, msgs = _cacheable(system, tools, messages)
    kw: dict[str, Any] = dict(model=model, max_tokens=max_tokens, system=sys_blocks, messages=msgs)
    if tl:
        kw["tools"] = tl
    want_think = bool(getattr(st, "dev_think", True)) if think is None else think
    if want_think and not STATE["think_refused"]:
        kw["thinking"] = {"type": "adaptive"}
    effort = getattr(PICK, "effort", "") or str(getattr(st, "dev_loop_effort", "high") or "")
    if effort and not STATE["effort_refused"]:
        kw["extra_body"] = {"output_config": {"effort": effort}}
    client = _client()
    with claude_only():
        for _ in range(3):
            try:
                resp = client.messages.create(**kw)
                break
            except Exception as e:
                if "thinking" in kw and _refused(e, "thinking"):
                    STATE["think_refused"] = True
                    kw.pop("thinking")
                    continue
                if "extra_body" in kw and (_refused(e, "effort") or _refused(e, "output_config")):
                    STATE["effort_refused"] = True
                    kw.pop("extra_body")
                    continue
                raise
        else:
            raise RuntimeError("the model refused every form of the call")
    STATE["calls"] += 1
    try:
        from .. import usage
        usage.from_anthropic(model, resp)
    except Exception:
        pass
    blocks = [b.model_dump(exclude_none=True) if hasattr(b, "model_dump") else dict(b) for b in resp.content]
    return blocks, str(getattr(resp, "stop_reason", "") or "")


def size(messages: list[dict]) -> int:
    """Characters in the conversation (a cheap stand-in for tokens: ~3.5 chars a token for code)."""
    n = 0
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            n += len(c)
            continue
        for b in c or []:
            if not isinstance(b, dict):
                continue
            for k in ("text", "thinking", "content", "input"):
                v = b.get(k)
                if isinstance(v, str):
                    n += len(v)
                elif v is not None:
                    n += len(str(v))
    return n


def trim(messages: list[dict], budget: int, keep: int = 6) -> int:
    """Over `budget` characters: replace the output of every tool result except the newest `keep` with a marker.
    In place, all at once (one cache break, not one per step). Returns how many were cleared."""
    if size(messages) <= budget:
        return 0
    spots: list[tuple[int, int]] = []
    for i, m in enumerate(messages):
        if m.get("role") != "user" or not isinstance(m.get("content"), list):
            continue
        for j, b in enumerate(m["content"]):
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("content") != CLEARED:
                spots.append((i, j))
    n = 0
    for i, j in spots[:-keep] if keep else spots:
        b = messages[i]["content"][j]
        if isinstance(b.get("content"), str) and len(b["content"]) < 400:
            continue                                   # short answers stay: clearing them saves nothing
        messages[i]["content"][j] = {**b, "content": CLEARED}
        n += 1
    STATE["cleared"] += n
    return n
