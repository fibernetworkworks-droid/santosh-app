"""HOOLA AEP hub - the init_chat_model router over Hoola's brains, the BYOK
adapter, the configurable model, the model-profiles registry + CLI - the
langchain `langchain/chat_models/base.py` + `langchain_model_profiles` idea
hand-built (upstream reference read at github.com/langchain-ai/langchain @
aa2528fb, libs/langchain_v1/langchain/chat_models/base.py 1079 lines: the
provider registry :56, init_chat_model :232, _ConfigurableModel :661;
libs/model-profiles/ cli.py 452 + _summary.py 493) - ZERO upstream code (the
port law).

v0.581.0 HOOLA HUB (P7 of the AEP plan):

- `init_chat_model(model, ...)` - the provider-string router: "provider:model"
  splits when the provider is known, a bare name is inferred from the house
  prefix table, an unknown provider refuses with the supported list. The house
  registry is HONEST by construction: it holds what the house actually has -
  "fake" (the deterministic test brains), "hoola" (the server's own brain lane
  behind an injected runner - never a settings read inside the AEP layer, the
  inertness law), "openai_compat" (the BYOK zoo: GLM, OmniRoute, vLLM,
  OpenRouter, any OpenAI-compatible endpoint - base_url + api_key ride the
  constructor). New providers join via `register_provider`.
- `ConfigurableModel` - the declarative mode: a model-less hub call returns a
  model that resolves per invoke from config["configurable"] (model,
  model_provider, temperature...), config_prefix for several models in one app,
  declarative calls (bind_tools / with_structured_output) queued until the real
  model exists - the upstream semantics, hand-built.
- `OpenAICompatChatModel` - the BYOK adapter: sync httpx against
  {base_url}/chat/completions, the OpenAI wire in and out (tool_calls parsed
  only when complete - the v0.221 house law), SSE streaming, tools bound via
  the declarative surface, `standard_params()` for the conformance suite and
  traces. The transport is injectable so the suites stay zero-network.
- `HouseBrainChatModel` - the server's own brain (claude/glm/omniroute) as a
  BaseChatModel: the runner is injected (sync or async), the lazy wiring lives
  in `hoola_brain_factory()` and imports the server lane only when CALLED.
- model profiles: `PROFILE_REGISTRY` (the living capability rows), `model_data_to_profile`
  (a models.dev-shaped row -> the house ModelProfile), `refresh_profiles`
  (generates the deterministic _profiles.py data file from a payload you hand
  it - the live models.dev fetch is upstream's lane; the house takes the data
  in, zero network), `summarize_profile_diff` (the reviewer's markdown), and
  the CLI: `python -m app.aep.hub profiles|refresh|diff`.

Inert library: nothing here reads settings, touches the network or spawns
threads on import - the P1 kill-switch note holds for P7 too.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import warnings
from typing import Any, Callable, Iterator, Literal, Sequence

from .messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from .models import BaseChatModel, ChatGeneration, ChatResult, FakeListChatModel
from .runnable import Runnable, RunnableBinding, ensure_config
from .tools import BaseTool

# ---------------------------------------------------------------------------
# the provider registry
# ---------------------------------------------------------------------------

ProviderFactory = Callable[..., BaseChatModel]

_FAKE_PROVIDER_NOTES = (
    "fake: the deterministic test brains (FakeListChatModel); "
    "hoola: the server's own brain behind an injected runner; "
    "openai_compat: any OpenAI-compatible endpoint (the BYOK zoo: GLM, "
    "OmniRoute, vLLM, OpenRouter, ...)"
)

_BUILTIN_PROVIDERS: dict[str, ProviderFactory] = {}

# The house prefix-inference table (upstream _attempt_infer_model_provider's
# shape, honest to the house: only what the house actually serves is inferred;
# everything else must name its provider explicitly).
_INFER_PREFIXES: dict[str, str] = {
    "fake-list": "fake",
    "claude": "hoola",
}


def register_provider(name: str, factory: ProviderFactory,
                      *, infer_prefixes: Sequence[str] = ()) -> None:
    """Join a provider to the hub (the upstream registry note: a provider not
    in the dict can still be used, but its key will not be inferred from the
    model name unless prefixes are declared here)."""
    if not name or not callable(factory):
        raise ValueError("register_provider needs a name and a factory callable")
    key = name.replace("-", "_").lower()
    _BUILTIN_PROVIDERS[key] = factory
    for prefix in infer_prefixes:
        _INFER_PREFIXES[prefix.lower()] = key


def known_providers() -> list[str]:
    return sorted(_BUILTIN_PROVIDERS)


def _fake_factory(model: str, **kwargs: Any) -> BaseChatModel:
    responses = kwargs.pop("responses", None) or [f"echo: {model}"]
    return FakeListChatModel(responses=responses, **kwargs)


def _hoola_factory(model: str, **kwargs: Any) -> BaseChatModel:
    return HouseBrainChatModel(model=model, **kwargs)


def _openai_compat_factory(model: str, **kwargs: Any) -> BaseChatModel:
    return OpenAICompatChatModel(model=model, **kwargs)


register_provider("fake", _fake_factory, infer_prefixes=["fake-list"])
register_provider("hoola", _hoola_factory, infer_prefixes=["claude"])
register_provider("openai_compat", _openai_compat_factory)


# ---------------------------------------------------------------------------
# parsing + inference (upstream base.py:547-651, hand-built)
# ---------------------------------------------------------------------------


def _attempt_infer_model_provider(model_name: str) -> str | None:
    model_lower = model_name.lower()
    for prefix, provider in _INFER_PREFIXES.items():
        if model_lower.startswith(prefix):
            return provider
    return None


def _parse_model(model: str, model_provider: str | None) -> tuple[str, str]:
    """The "provider:model" split + the prefix inference (upstream _parse_model)."""
    if (not model_provider and ":" in model
            and model.split(":", maxsplit=1)[0] in _BUILTIN_PROVIDERS):
        model_provider = model.split(":", maxsplit=1)[0]
        model = ":".join(model.split(":")[1:])
    model_provider = model_provider or _attempt_infer_model_provider(model)
    if not model_provider:
        supported_list = ", ".join(sorted(_BUILTIN_PROVIDERS))
        raise ValueError(
            f"Unable to infer model provider for {model=}. "
            "Please specify 'model_provider' directly.\n\n"
            f"Supported providers: {supported_list}\n\n"
            f"House providers: {_FAKE_PROVIDER_NOTES}")
    model_provider = model_provider.replace("-", "_").lower()
    if model_provider not in _BUILTIN_PROVIDERS:
        supported_list = ", ".join(sorted(_BUILTIN_PROVIDERS))
        raise ValueError(
            f"Unsupported {model_provider=}.\n\nSupported model providers are: "
            f"{supported_list}")
    return model, model_provider


def _init_chat_model_helper(model: str, *, model_provider: str | None = None,
                            **kwargs: Any) -> BaseChatModel:
    model, model_provider = _parse_model(model, model_provider)
    creator = _BUILTIN_PROVIDERS[model_provider]
    return creator(model, **kwargs)


# ---------------------------------------------------------------------------
# the configurable model (upstream _ConfigurableModel, hand-built)
# ---------------------------------------------------------------------------

_DECLARATIVE_METHODS = ("bind_tools", "with_structured_output")


class ConfigurableModel(Runnable):
    """The declarative mode: the real model resolves per call from config.

    - Built model-less (`init_chat_model()` with no model): every invoke needs
      config["configurable"]["model"] (+ optional model_provider).
    - Built with a default: the default rides unless the config overrides it.
    - `configurable_fields` filters what the config may set ("any" or a list).
    - `config_prefix` names the config keys (`{prefix}_model`) so several
      configurable models can live in one app without key collisions.
    - Declarative calls (bind_tools / with_structured_output) are QUEUED and
      applied to whichever model the config resolves - the upstream law.
    """

    def __init__(self, *, default_config: dict[str, Any] | None = None,
                 configurable_fields: Literal["any"] | list[str] | tuple[str, ...] = "any",
                 config_prefix: str = "",
                 queued_declarative_operations: Sequence[tuple[str, tuple, dict]] = (),
                 pinned_config: dict[str, Any] | None = None) -> None:
        self._default_config: dict[str, Any] = dict(default_config or {})
        self._configurable_fields: Literal["any"] | list[str] = (
            "any" if configurable_fields == "any" else list(configurable_fields))
        self._config_prefix = (
            config_prefix + "_" if config_prefix and not config_prefix.endswith("_")
            else config_prefix)
        self._queued_declarative_operations: list[tuple[str, tuple, dict]] = list(
            queued_declarative_operations or ())
        self._pinned_config: dict[str, Any] = dict(pinned_config or {})

    # -- resolution ----------------------------------------------------------

    def _model_params(self, config: dict | None) -> dict[str, Any]:
        cfg = ensure_config(config)
        params = {
            k.removeprefix(self._config_prefix): v
            for k, v in (cfg.get("configurable") or {}).items()
            if k.startswith(self._config_prefix)
        }
        if self._configurable_fields != "any":
            params = {k: v for k, v in params.items() if k in self._configurable_fields}
        return params

    def _model(self, config: dict | None = None) -> Runnable:
        # the resolution ladder: defaults <- with_config's pinned params <- per-call
        params = {**self._default_config,
                  **self._model_params(self._pinned_config),
                  **self._model_params(config)}
        if "model" not in params:
            raise ValueError(
                "No model configured: pass config={'configurable': {'model': "
                "'provider:model'}} or build with a default model")
        model_name = params.pop("model")
        model_provider = params.pop("model_provider", None)
        model = _init_chat_model_helper(model_name, model_provider=model_provider, **params)
        for name, args, kwargs in self._queued_declarative_operations:
            model = getattr(model, name)(*args, **kwargs)
        return model

    # -- the Runnable surface rides the resolved model ------------------------

    def invoke(self, input: Any, config: dict | None = None,  # noqa: A002,A003
               **kwargs: Any) -> Any:
        merged = {**self._pinned_config, **(config or {})}
        return self._model(merged).invoke(input, config=merged, **kwargs)

    async def ainvoke(self, input: Any, config: dict | None = None,  # noqa: A002,A003
                      **kwargs: Any) -> Any:
        merged = {**self._pinned_config, **(config or {})}
        return await self._model(merged).ainvoke(input, config=merged, **kwargs)

    def stream(self, input: Any, config: dict | None = None,  # noqa: A002,A003
               **kwargs: Any) -> Iterator[Any]:
        merged = {**self._pinned_config, **(config or {})}
        yield from self._model(merged).stream(input, config=merged, **kwargs)

    def batch(self, inputs: list[Any], config: Any = None, *,
              return_exceptions: bool = False, **kwargs: Any) -> list[Any]:
        merged = {**self._pinned_config, **(config or {})}
        return self._model(merged).batch(inputs, config=merged,
                                         return_exceptions=return_exceptions, **kwargs)

    def __getattr__(self, name: str) -> Any:
        if name in _DECLARATIVE_METHODS:
            def queue(*args: Any, **kwargs: Any) -> "ConfigurableModel":
                return ConfigurableModel(
                    default_config=dict(self._default_config),
                    configurable_fields=list(self._configurable_fields)
                    if isinstance(self._configurable_fields, list)
                    else self._configurable_fields,
                    config_prefix=self._config_prefix,
                    queued_declarative_operations=[
                        *self._queued_declarative_operations, (name, args, kwargs)],
                )
            return queue
        raise AttributeError(
            f"{name} is not a ConfigurableModel attribute. Resolve a model first "
            "(pass a config with 'model') or queue a declarative call "
            "(bind_tools / with_structured_output).")

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable:
        return self.__getattr__("bind_tools")(tools, **kwargs)  # noqa: PLC2801

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Runnable:
        return self.__getattr__("with_structured_output")(schema, **kwargs)  # noqa: PLC2801

    def with_config(self, config: dict | None = None, **kwargs: Any) -> "ConfigurableModel":
        merged = {**(config or {}), **kwargs}
        cfg = ensure_config(merged)
        model_params = self._model_params(cfg)
        remaining = {k: v for k, v in cfg.items() if k != "configurable"}
        remaining["configurable"] = {
            k: v for k, v in (cfg.get("configurable") or {}).items()
            if k.removeprefix(self._config_prefix) not in model_params
        }
        queued = list(self._queued_declarative_operations)
        # with_config does NOT queue: the house Runnable surface has no
        # with_config method - the remaining config is PINNED (merged under
        # every later call's config) instead, which lands the same semantics.
        return ConfigurableModel(
            default_config={**self._default_config, **model_params},
            configurable_fields=self._configurable_fields,
            config_prefix=self._config_prefix,
            queued_declarative_operations=queued,
            pinned_config={**self._pinned_config, **remaining},
        )


# ---------------------------------------------------------------------------
# init_chat_model (upstream base.py:232, hand-built)
# ---------------------------------------------------------------------------


def init_chat_model(
    model: str | None = None,
    *,
    model_provider: str | None = None,
    configurable_fields: Literal["any"] | list[str] | tuple[str, ...] | None = None,
    config_prefix: str | None = None,
    **kwargs: Any,
) -> BaseChatModel | ConfigurableModel:
    """The unified router: a model string in, a chat model out.

    Two modes (the upstream contract):
    - FIXED: `init_chat_model("fake:echo", responses=[...])` /
      `init_chat_model("hoola:claude-sonnet-5-5", runner=...)` /
      `init_chat_model("openai_compat:glm-4.7", base_url=..., api_key=...)`
      -> a ready BaseChatModel.
    - CONFIGURABLE: build model-less (or with
      `configurable_fields=("model", "model_provider")`) -> a ConfigurableModel
      that resolves per call from config["configurable"].

    The house registry is honest: fake | hoola | openai_compat are built in;
    `register_provider` joins more (the BYOK zoo extension lane).
    """
    if model is not None and not isinstance(model, str):
        raise TypeError(
            "`model` must be a string (e.g., 'openai_compat:glm-4.7'), got "
            f"{type(model).__name__}. If you've already constructed a chat model "
            "object, use it directly instead of passing it to init_chat_model().")
    if not model and not configurable_fields:
        configurable_fields = ("model", "model_provider")
    config_prefix = config_prefix or ""
    if config_prefix and not configurable_fields:
        warnings.warn(
            f"{config_prefix=} has been set but no fields are configurable. Set "
            "`configurable_fields=(...)` to specify the model params that are "
            "configurable.", stacklevel=2)
    if not configurable_fields:
        return _init_chat_model_helper(model or "", model_provider=model_provider, **kwargs)
    if model:
        kwargs["model"] = model
    if model_provider:
        kwargs["model_provider"] = model_provider
    return ConfigurableModel(
        default_config=kwargs,
        config_prefix=config_prefix,
        configurable_fields=configurable_fields,
    )


# ---------------------------------------------------------------------------
# the BYOK adapter (the OpenAI-compatible zoo)
# ---------------------------------------------------------------------------


def _message_to_openai(m: BaseMessage) -> dict[str, Any]:
    role = {"human": "user", "ai": "assistant", "system": "system",
            "tool": "tool"}.get(m.type, "user")
    out: dict[str, Any] = {"role": role, "content": m.text if hasattr(m, "text") else m.content}
    if role == "assistant" and getattr(m, "tool_calls", None):
        out["tool_calls"] = [
            {"id": tc.get("id") or f"call_{i}", "type": "function",
             "function": {"name": tc.get("name") or "",
                          "arguments": json.dumps(tc.get("args") or {}, ensure_ascii=False)}}
            for i, tc in enumerate(m.tool_calls)]
        if not out["content"]:
            out["content"] = None
    if role == "tool":
        out["tool_call_id"] = getattr(m, "tool_call_id", "")
    return out


def _tools_to_openai(tools: Sequence[Any]) -> list[dict[str, Any]]:
    """House tools (BaseTool / pydantic / dict schema) -> the OpenAI functions wire."""
    out: list[dict[str, Any]] = []
    for t in tools:
        if isinstance(t, BaseTool):
            schema = t.tool_call_schema
            params = (schema.model_json_schema() if isinstance(schema, type)
                      and hasattr(schema, "model_json_schema")
                      else schema if isinstance(schema, dict) else {"type": "object", "properties": {}})
            out.append({"type": "function", "function": {
                "name": t.name, "description": t.description or "", "parameters": params}})
        elif isinstance(t, type) and hasattr(t, "model_json_schema"):
            schema = t.model_json_schema()
            out.append({"type": "function", "function": {
                "name": schema.get("title", t.__name__),
                "description": schema.get("description", ""), "parameters": schema}})
        elif isinstance(t, dict) and "function" in t:
            out.append(t)
        elif isinstance(t, dict):
            name = t.get("name") or "tool"
            out.append({"type": "function", "function": {
                "name": name, "description": t.get("description", ""),
                "parameters": t.get("parameters") or {"type": "object", "properties": {}}}})
        else:
            raise ValueError(f"Unsupported tool for the OpenAI wire: {type(t).__name__}")
    return out


class OpenAICompatChatModel(BaseChatModel):
    """Any OpenAI-compatible /chat/completions endpoint as a house chat model.

    The BYOK zoo lane: GLM, OmniRoute, a self-hosted vLLM/SGLang, OpenRouter -
    base_url + api_key + model ride the constructor (BYOK = the caller's keys,
    never the AEP layer's config reads - the inertness law). `transport`
    injects an httpx transport so the suites stay zero-network (httpx
    MockTransport). Tool calls are parsed only when complete (the v0.221 house
    law: never run a tool on half-written arguments).
    """

    model: str
    base_url: str
    api_key: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_s: float = 60.0
    transport: Any = None
    extra_headers: dict[str, str] = {}

    lc_secrets: ClassVar[dict[str, str]] = {"api_key": "BYOK_API_KEY"}
    """The P7 secrets law: dumpd() masks api_key as the $placeholder so the
    BYOK key never rides a serialized payload (load substitutes from
    secrets_map - or refuses)."""

    @property
    def _llm_type(self) -> str:
        return "openai-compat"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model": self.model, "base_url": self.base_url}

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", **self.extra_headers}
        httpx = importlib.import_module("httpx")  # the P1 lazy-import law: never on module load
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_s,
                              transport=self.transport) as client:
                r = client.post("/chat/completions", json=body, headers=headers)
        except httpx.HTTPError as e:
            raise ValueError(f"OpenAI-compatible endpoint not reachable: {e}") from e
        if r.status_code >= 400:
            raise ValueError(f"OpenAI-compatible endpoint error {r.status_code}: {r.text[:300]}")
        try:
            return r.json()
        except ValueError as e:
            raise ValueError(f"OpenAI-compatible endpoint sent a broken answer: {e}") from e

    def _build_body(self, messages: list[BaseMessage], tools: Sequence[Any] | None,
                    **kwargs: Any) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": kwargs.pop("model", None) or self.model,
            "messages": [_message_to_openai(m) for m in messages],
        }
        temperature = kwargs.pop("temperature", self.temperature)
        if temperature is not None:
            body["temperature"] = temperature
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        stop = kwargs.pop("stop", None)
        if stop:
            body["stop"] = stop
        if tools:
            body["tools"] = _tools_to_openai(tools)
            body["tool_choice"] = kwargs.pop("tool_choice", "auto")
        return body

    def _parse_response(self, data: dict[str, Any]) -> ChatResult:
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        raw_calls = msg.get("tool_calls") or []
        tool_calls: list[dict[str, Any]] = []
        broken = 0
        for i, tc in enumerate(raw_calls):
            fn = tc.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
                if not isinstance(args, dict):
                    args = {}
            except json.JSONDecodeError:
                broken += 1     # half-written arguments = a cut answer: the call is DROPPED
                continue
            tool_calls.append({"type": "tool_call", "id": tc.get("id") or f"call_{i}",
                               "name": fn.get("name", ""), "args": args, "index": i})
        usage = dict(data.get("usage") or {})
        usage_metadata: dict[str, int] = {}
        if usage:
            usage_metadata = {
                "input_tokens": int(usage.get("prompt_tokens") or 0),
                "output_tokens": int(usage.get("completion_tokens") or 0),
            }
            usage_metadata["total_tokens"] = (usage_metadata["input_tokens"]
                                              + usage_metadata["output_tokens"])
        finish = choice.get("finish_reason") or ""
        if broken and not tool_calls:
            finish = "length"   # a cut answer is NOT a finished answer
        ai = AIMessage(
            content=msg.get("content") or "",
            tool_calls=tool_calls,
            response_metadata={"finish_reason": finish, "model": data.get("model")},
            usage_metadata=usage_metadata or None,
        )
        return ChatResult(generations=[ChatGeneration(message=ai)],
                          llm_output={"model_name": self._llm_type})

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None,  # noqa: ARG002
                  **kwargs: Any) -> ChatResult:
        tools = kwargs.pop("tools", None)
        body = self._build_body(messages, tools, **kwargs)
        return self._parse_response(self._post(body))

    def _stream(self, messages: list[BaseMessage], stop: list[str] | None = None,  # noqa: ARG002
                **kwargs: Any) -> Iterator[AIMessageChunk]:
        tools = kwargs.pop("tools", None)
        body = self._build_body(messages, tools, **kwargs)
        body["stream"] = True
        headers = {"Authorization": f"Bearer {self.api_key}", **self.extra_headers}
        httpx = importlib.import_module("httpx")  # the P1 lazy-import law: never on module load
        text_parts: list[str] = []
        calls: dict[int, dict[str, str]] = {}
        finish = ""
        usage: dict[str, Any] = {}
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_s,
                              transport=self.transport) as client:
                with client.stream("POST", "/chat/completions", json=body,
                                   headers=headers) as r:
                    if r.status_code >= 400:
                        detail = r.read().decode("utf-8", "replace")[:300]
                        raise ValueError(
                            f"OpenAI-compatible endpoint error {r.status_code}: {detail}")
                    for line in r.iter_lines():
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
                                text_parts.append(d["content"])
                                yield AIMessageChunk(content=d["content"])
                            for tc in d.get("tool_calls") or []:
                                c = calls.setdefault(int(tc.get("index") or 0),
                                                     {"id": "", "name": "", "args": ""})
                                fn = tc.get("function") or {}
                                c["id"] = tc.get("id") or c["id"]
                                c["name"] += fn.get("name") or ""
                                c["args"] += fn.get("arguments") or ""
        except httpx.HTTPError as e:
            raise ValueError(f"OpenAI-compatible endpoint not reachable: {e}") from e
        if calls:
            # Tool calls join and parse only when the answer is complete - never partial JSON.
            usage_metadata: dict[str, int] = {}
            if usage:
                usage_metadata = {
                    "input_tokens": int(usage.get("prompt_tokens") or 0),
                    "output_tokens": int(usage.get("completion_tokens") or 0),
                }
                usage_metadata["total_tokens"] = (usage_metadata["input_tokens"]
                                                  + usage_metadata["output_tokens"])
            final = AIMessageChunk(content="")
            final = final + AIMessageChunk(
                content="",
                tool_calls=[{"type": "tool_call", "id": c["id"] or f"call_{i}",
                             "name": c["name"], "args": _safe_json(c["args"]),
                             "index": i} for i, c in sorted(calls.items())],
                tool_call_chunks=[
                    {"name": c["name"], "args": c["args"], "id": c["id"] or f"call_{i}",
                     "index": i, "type": "tool_call_chunk"} for i, c in sorted(calls.items())],
                response_metadata={"finish_reason": finish},
                usage_metadata=usage_metadata or None,
            )
            yield final
        elif usage:
            # A text-only stream still carries the usage row on a final empty chunk
            # so traces never miscount the call.
            usage_metadata = {
                "input_tokens": int(usage.get("prompt_tokens") or 0),
                "output_tokens": int(usage.get("completion_tokens") or 0),
            }
            usage_metadata["total_tokens"] = (usage_metadata["input_tokens"]
                                              + usage_metadata["output_tokens"])
            yield AIMessageChunk(content="", usage_metadata=usage_metadata,
                                 response_metadata={"finish_reason": finish})

    # -- the declarative surface ---------------------------------------------

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable:
        return RunnableBinding(bound=self, kwargs={"tools": list(tools), **kwargs})

    def standard_params(self, *, model: str | None = None) -> dict[str, Any]:
        """The trace row (the upstream _get_ls_params shape): which provider,
        which model - honoring a per-call model override so traces never
        misattribute a call."""
        return {
            "ls_provider": "openai_compat",
            "ls_model_name": model or self.model,
            "ls_model_type": "chat",
            "ls_temperature": self.temperature,
            "ls_max_tokens": self.max_tokens,
        }


def _safe_json(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw) if raw else {}
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# the hoola brain adapter (the server's own lane behind an injected runner)
# ---------------------------------------------------------------------------


class HouseBrainChatModel(BaseChatModel):
    """The server's own brain as a house chat model - claude / glm / omniroute.

    The RUNNER is injected (a callable (messages, tools, kwargs) -> ChatResult
    or an async twin); the AEP layer never reads settings or env itself - the
    inertness law. `hoola_brain_factory()` below is the lazy wiring lane: it
    imports the server's brain module only when CALLED, builds the runner, and
    hands back a ready model.
    """

    model: str = "auto"
    runner: Any = None

    @property
    def _llm_type(self) -> str:
        return "hoola-brain"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model": self.model}

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None,
                  **kwargs: Any) -> ChatResult:
        if self.runner is None:
            raise ValueError(
                "HouseBrainChatModel has no runner wired - build it through "
                "hoola_brain_factory() (which lazily imports the server lane) or "
                "pass runner=<callable> explicitly")
        tools = kwargs.pop("tools", None)
        result = self.runner(messages, tools, **kwargs)
        if not isinstance(result, ChatResult):
            raise ValueError(
                f"The brain runner returned {type(result).__name__}; the hub "
                "contract is a ChatResult")
        return result

    async def ainvoke(self, input: Any, config: dict | None = None,  # noqa: A002,A003
                      **kwargs: Any) -> AIMessage:
        import asyncio
        import inspect
        messages = _convert_messages(input)
        if self.runner is not None and inspect.iscoroutinefunction(self.runner):
            tools = kwargs.pop("tools", None)
            result = await self.runner(messages, tools, **kwargs)
            if not isinstance(result, ChatResult):
                raise ValueError(
                    f"The brain runner returned {type(result).__name__}; the hub "
                    "contract is a ChatResult")
            cfg = ensure_config(config)
            span = _span_start(cfg, self, "chat_model", messages)
            out = result.generations[0].message
            if span is not None:
                span.end(out)
            return out
        return await super().ainvoke(input, config, **kwargs)

    def standard_params(self, *, model: str | None = None) -> dict[str, Any]:
        return {"ls_provider": "hoola", "ls_model_name": model or self.model,
                "ls_model_type": "chat"}


def _convert_messages(input_value: Any) -> list[BaseMessage]:
    from .models import _convert_to_messages
    return _convert_to_messages(input_value)


def _span_start(cfg: dict, obj: Any, run_type: str, inputs: Any):
    if not (cfg or {}).get("callbacks"):
        return None
    from .tracers import Span
    return Span.start(cfg, obj, run_type, inputs)


def hoola_brain_factory(brain: str = "auto", *, model: str | None = None,
                        runner: Any = None, **kwargs: Any) -> HouseBrainChatModel:
    """The lazy wiring lane for the server's own brains.

    With an explicit `runner` (the test lane), no server import happens. The
    live lane wires the OpenAI-compatible server brains by importing
    app.agent.llm INSIDE this call - the import never happens on module load
    (the inertness law) and only for the brains the server actually routes.
    """
    if runner is not None:
        return HouseBrainChatModel(model=model or brain, runner=runner, **kwargs)
    try:
        from app.agent import llm as server_llm  # the lazy import - inert until here
    except ImportError as e:
        raise ValueError(
            "hoola_brain_factory() lives on the server; outside the server pass "
            "runner=<callable> explicitly") from e

    import asyncio

    async def _run(messages: list[BaseMessage], tools: Any, **kw: Any) -> ChatResult:
        st_system = ""
        st_messages = []
        for m in messages:
            if isinstance(m, SystemMessage):
                st_system = m.text
                continue
            st_messages.append({"role": "user" if m.type == "human" else "assistant",
                                "content": m.content})
        chosen = brain
        if brain == "auto":
            chosen = server_llm.choose(st_messages)
        blocks, stop, usage = await server_llm.openai_create(
            chosen, st_system, list(tools or []), st_messages,
            int(kw.pop("max_tokens", 4096)))
        tool_calls = [
            {"type": "tool_call", "id": b.get("id") or f"call_{i}",
             "name": b.get("name", ""), "args": b.get("input") or {}, "index": i}
            for i, b in enumerate(blocks) if b.get("type") == "tool_use"]
        text = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return ChatResult(generations=[ChatGeneration(message=AIMessage(
            content=text, tool_calls=tool_calls,
            response_metadata={"stop_reason": stop}, usage_metadata={
                "input_tokens": int(usage.get("prompt_tokens") or 0),
                "output_tokens": int(usage.get("completion_tokens") or 0),
                "total_tokens": (int(usage.get("prompt_tokens") or 0)
                                 + int(usage.get("completion_tokens") or 0)),
            } if usage else None))],
            llm_output={"model_name": "hoola-brain"})

    return HouseBrainChatModel(model=model or brain, runner=_run, **kwargs)


# ---------------------------------------------------------------------------
# model profiles (upstream libs/model-profiles, hand-built)
# ---------------------------------------------------------------------------

PROFILE_REGISTRY: dict[str, dict[str, Any]] = {
    "fake-list-chat": {
        "name": "FakeListChatModel", "status": "test",
        "text_inputs": True, "image_inputs": False, "audio_inputs": False,
        "tool_calling": False, "structured_output": False,
    },
    "openai-compat": {
        "name": "OpenAICompatChatModel", "status": "beta",
        "text_inputs": True, "image_inputs": False, "audio_inputs": False,
        "tool_calling": True, "structured_output": True,
    },
    "hoola-brain": {
        "name": "HouseBrainChatModel", "status": "beta",
        "text_inputs": True, "image_inputs": False, "audio_inputs": False,
        "tool_calling": True, "structured_output": True,
    },
}
"""The living capability rows (upstream ModelProfile + the _profiles.py idea;
the docs7 law: rows live, the model never judges them)."""

PROFILE_KEYS = ("name", "status", "release_date", "max_input_tokens",
                "max_output_tokens", "text_inputs", "image_inputs",
                "audio_inputs", "tool_calling", "structured_output")

_FIELD_LABELS = {
    "name": "display name", "status": "status", "release_date": "release date",
    "max_input_tokens": "max input tokens", "max_output_tokens": "max output tokens",
    "text_inputs": "text input", "image_inputs": "image input",
    "audio_inputs": "audio input", "tool_calling": "tool calling",
    "structured_output": "structured output",
}


def model_data_to_profile(model_data: dict[str, Any]) -> dict[str, Any]:
    """A models.dev-shaped row -> the house ModelProfile keys
    (upstream cli.py:_model_data_to_profile ported; undeclared keys WARN and
    ride dropped - the upstream behavior)."""
    profile: dict[str, Any] = {}
    if model_data.get("name"):
        profile["name"] = model_data["name"]
    for src, dst in (("status", "status"), ("release_date", "release_date")):
        if model_data.get(src):
            profile[dst] = model_data[src]
    limit = model_data.get("limit") or {}
    if isinstance(limit, dict):
        if limit.get("context"):
            profile["max_input_tokens"] = int(limit["context"])
        if limit.get("output"):
            profile["max_output_tokens"] = int(limit["output"])
    modalities = model_data.get("modalities") or {}
    if isinstance(modalities, dict):
        inputs = modalities.get("input") or []
        profile["text_inputs"] = "text" in inputs
        profile["image_inputs"] = "image" in inputs
        profile["audio_inputs"] = "audio" in inputs
    for src, dst in (("tool_call", "tool_calling"),
                     ("structured_output", "structured_output")):
        if src in model_data:
            profile[dst] = bool(model_data[src])
    known = {"id", "name", "status", "release_date", "limit", "modalities",
             "tool_call", "structured_output"}
    unknown = sorted(set(model_data) - known)
    if unknown:
        warnings.warn(f"Undeclared profile keys dropped: {unknown}", stacklevel=2)
    return profile


def refresh_profiles(payload: dict[str, Any], out_path: str | None = None) -> dict[str, Any]:
    """Generate the profile data file from a models.dev-shaped payload you hand
    in (upstream refresh() hits models.dev live; the house takes the data in -
    zero network, the same generated-artifact law). Deterministic: sorted keys,
    indent 2 - the same payload writes byte-stable files."""
    profiles: dict[str, dict[str, Any]] = {}
    for provider in sorted(payload):
        for model_id in sorted(payload[provider]):
            row = dict(payload[provider][model_id])
            row.setdefault("name", model_id)
            profiles[f"{provider}/{model_id}"] = model_data_to_profile(row)
    stats = {"providers": len(payload), "models": len(profiles), "written": False}
    if out_path:
        body = "# Generated by app.aep.hub (P7 model-profiles) - do not edit by hand.\n"
        body += "PROFILES: dict[str, dict] = "
        body += json.dumps(profiles, indent=2, sort_keys=True) + "\n"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(body)
        stats["written"] = True
    return stats


def summarize_profile_diff(old: dict[str, Any], new: dict[str, Any]) -> str:
    """The reviewer's markdown: new / removed / changed rows, deterministic
    (upstream _summary.py ported, the 25-row cap per section included)."""
    lines: list[str] = []
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    if added:
        lines.append("## New models\n")
        for key in added[:25]:
            lines.append(f"- `{key}`: {_fmt_profile(new[key])}")
        if len(added) > 25:
            lines.append(f"- ... and {len(added) - 25} more")
    if removed:
        lines.append("## Removed models\n")
        for key in removed[:25]:
            lines.append(f"- `{key}`")
        if len(removed) > 25:
            lines.append(f"- ... and {len(removed) - 25} more")
    changed_rows: list[str] = []
    for key in sorted(set(old) & set(new)):
        diffs = _fmt_changes(old[key] or {}, new[key] or {})
        if diffs:
            changed_rows.append(f"- `{key}`: {'; '.join(diffs)}")
    if changed_rows:
        lines.append("## Changed\n")
        lines.extend(changed_rows[:25])
        if len(changed_rows) > 25:
            lines.append(f"- ... and {len(changed_rows) - 25} more")
    if not lines:
        lines.append("No profile changes.")
    return "\n".join(lines) + "\n"


def _fmt_profile(p: dict[str, Any]) -> str:
    bits = [f"{_FIELD_LABELS.get(k, k)} {v}" for k, v in sorted((p or {}).items())]
    return ", ".join(bits) if bits else "empty profile"


def _fmt_changes(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key in sorted(set(a) | set(b)):
        va, vb = a.get(key), b.get(key)
        if va != vb:
            label = _FIELD_LABELS.get(key, key)
            out.append(f"{label}: {va!r} -> {vb!r}")
    return out


# ---------------------------------------------------------------------------
# the CLI (upstream cli.py's shape, zero network)
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.aep.hub",
        description="HOOLA AEP model-profiles CLI (the P7 analog of the "
                    "upstream model-profiles refresh/diff tooling; zero network "
                    "- data rides in as JSON files).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("profiles", help="print the profile registry")
    p_list.add_argument("--format", choices=("table", "json"), default="table")
    p_list.add_argument("--registry", help="optional JSON file with extra rows")
    p_list.add_argument("--check", action="store_true",
                        help="validate every row against the house profile keys")

    p_refresh = sub.add_parser("refresh", help="generate _profiles.py from a models.dev-shaped JSON")
    p_refresh.add_argument("--from", dest="src", required=True)
    p_refresh.add_argument("--out", dest="out", required=True)

    p_diff = sub.add_parser("diff", help="markdown summary of two registry JSONs")
    p_diff.add_argument("--old", required=True)
    p_diff.add_argument("--new", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "profiles":
        rows = dict(PROFILE_REGISTRY)
        if args.registry:
            with open(args.registry, encoding="utf-8") as f:
                rows.update(json.load(f))
        if args.check:
            bad = {k: sorted(set(v) - set(PROFILE_KEYS)) for k, v in rows.items()
                   if set(v) - set(PROFILE_KEYS)}
            if bad:
                print(json.dumps({"ok": False, "undeclared": bad}, indent=2))
                return 1
            print(json.dumps({"ok": True, "rows": len(rows)}))
            return 0
        if args.format == "json":
            print(json.dumps(rows, indent=2, sort_keys=True))
        else:
            for key in sorted(rows):
                print(f"{key}\t{_fmt_profile(rows[key])}")
        return 0

    if args.cmd == "refresh":
        with open(args.src, encoding="utf-8") as f:
            payload = json.load(f)
        stats = refresh_profiles(payload, args.out)
        print(json.dumps(stats, indent=2, sort_keys=True))
        return 0

    if args.cmd == "diff":
        with open(args.old, encoding="utf-8") as f:
            old = json.load(f)
        with open(args.new, encoding="utf-8") as f:
            new = json.load(f)
        sys.stdout.write(summarize_profile_diff(old, new))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
