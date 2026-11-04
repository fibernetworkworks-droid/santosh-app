"""HOOLA AEP models - the chat model contract, the langchain-core
`language_models/` idea hand-built (upstream reference:
language_models/chat_models.py:325 BaseChatModel, llms.py BaseLLM, caches.py:32
BaseCache/155 InMemoryCache, rate_limiters.py:67 InMemoryRateLimiter,
model_profile.py:13 ModelProfile, fake_chat_models.py).

v0.510.0 HOOLA CORE: the imperative surface (invoke / generate / batch / stream)
and the declarative surface (bind_tools, with_structured_output, with_retry,
with_fallbacks); a subclass owes only `_generate` + `_llm_type`. Token-bucket rate
limiter and generation cache are built in; ModelProfile is the capability row
(living-rows hook for P7 - the docs7 law). FakeListChatModel/FakeListLLM give the
suites deterministic brains. Inert library; nothing calls a network here.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Iterator, Sequence, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from .messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from .runnable import Runnable, RunnableConfig, RunnableSerializable, ensure_config
from .prompts import PromptValue

class UsageMetadata(TypedDict, total=False):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ModelProfile(TypedDict, total=False):
    """Capability metadata row (upstream model_profile.py:13; data becomes living rows)."""

    name: str
    status: str
    release_date: str
    max_input_tokens: int
    max_output_tokens: int
    text_inputs: bool
    image_inputs: bool
    audio_inputs: bool
    tool_calling: bool
    structured_output: bool


# ---------------------------------------------------------------------------
# generations
# ---------------------------------------------------------------------------


class ChatGeneration(BaseModel):
    message: AIMessage
    generation_info: dict[str, Any] = Field(default_factory=dict)


class ChatResult(BaseModel):
    generations: list[ChatGeneration]
    llm_output: dict[str, Any] = Field(default_factory=dict)


class Generation(BaseModel):
    text: str
    generation_info: dict[str, Any] = Field(default_factory=dict)


class LLMResult(BaseModel):
    generations: list[list[Generation]]
    llm_output: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# cache + rate limiter (upstream caches.py, rate_limiters.py)
# ---------------------------------------------------------------------------


class BaseCache(ABC):
    @abstractmethod
    def lookup(self, prompt: str, llm_string: str) -> ChatResult | None: ...

    @abstractmethod
    def update(self, prompt: str, llm_string: str, result: ChatResult) -> None: ...


class InMemoryCache(BaseCache):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: dict[tuple[str, str], ChatResult] = {}

    def lookup(self, prompt: str, llm_string: str) -> ChatResult | None:
        with self._lock:
            return self._cache.get((prompt, llm_string))

    def update(self, prompt: str, llm_string: str, result: ChatResult) -> None:
        with self._lock:
            self._cache[(prompt, llm_string)] = result


class BaseRateLimiter(ABC):
    @abstractmethod
    def acquire(self, *, blocking: bool = True) -> bool: ...


class InMemoryRateLimiter(BaseRateLimiter):
    """Thread-safe token bucket (upstream rate_limiters.py:67)."""

    def __init__(self, *, rate_limit_per_second: float = 1.0,
                 max_bucket_size: float = 1.0) -> None:
        if rate_limit_per_second <= 0:
            raise ValueError("rate_limit_per_second must be positive")
        self.rate_limit_per_second = rate_limit_per_second
        self.max_bucket_size = max_bucket_size
        self._lock = threading.Lock()
        self._tokens = float(max_bucket_size)
        self._last = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        self._tokens = min(self.max_bucket_size,
                           self._tokens + (now - self._last) * self.rate_limit_per_second)
        self._last = now

    def acquire(self, *, blocking: bool = True) -> bool:
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return True
                wait = (1 - self._tokens) / self.rate_limit_per_second
            if not blocking:
                return False
            time.sleep(min(wait, 0.25))


# ---------------------------------------------------------------------------
# the model contracts
# ---------------------------------------------------------------------------


def _convert_to_messages(
    input_value: str | list[Any] | PromptValue,
) -> list[BaseMessage]:
    if isinstance(input_value, str):
        return [HumanMessage(content=input_value)]
    if isinstance(input_value, PromptValue):
        return input_value.to_messages()
    out: list[BaseMessage] = []
    for m in input_value:
        if isinstance(m, BaseMessage):
            out.append(m)
        elif isinstance(m, str):
            out.append(HumanMessage(content=m))
        elif isinstance(m, dict):
            role = m.get("role", "human")
            content = m.get("content", "")
            from .messages import ChatMessage, ToolMessage
            role_cls = {"human": HumanMessage, "user": HumanMessage,
                        "ai": AIMessage, "assistant": AIMessage,
                        "system": SystemMessage, "tool": ToolMessage}
            cls = role_cls.get(role)
            if cls is None:
                out.append(ChatMessage(role=role, content=content))
            else:
                out.append(cls(content=content))
        else:
            raise TypeError(f"Unsupported message in model input: {type(m).__name__}")
    return out


class _SerializableBase(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")


class BaseLLM(_SerializableBase, Runnable[str, str]):
    """The completion-model contract (upstream llms.py): _generate + _llm_type."""

    rate_limiter: BaseRateLimiter | None = None
    cache: BaseCache | None = None
    profile: ModelProfile | None = None

    @property
    @abstractmethod
    def _llm_type(self) -> str: ...

    @abstractmethod
    def _generate(self, prompts: list[str], stop: list[str] | None = None,
                  **kwargs: Any) -> LLMResult: ...

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {}

    def _llm_string(self) -> str:
        return f"{type(self).__name__}:{self._llm_type}:{sorted(self._identifying_params.items())}"

    def _generate_with_cache(self, prompt: str, stop: list[str] | None, **kwargs: Any) -> LLMResult:
        cache = self.cache
        if cache is not None:
            hit = cache.lookup(prompt, self._llm_string())
            if hit is not None:
                return hit
        if self.rate_limiter is not None:
            self.rate_limiter.acquire()
        result = self._generate([prompt], stop=stop, **kwargs)
        if cache is not None:
            cache.update(prompt, self._llm_string(), result)  # type: ignore[arg-type]
        return result

    def invoke(self, input: str, config: RunnableConfig | None = None,  # noqa: A002,A003
               *, stop: list[str] | None = None, **kwargs: Any) -> str:
        cfg = ensure_config(config)
        kwargs = {**cfg.get("kwargs", {}), **kwargs}
        result = self._generate_with_cache(input, stop, **kwargs)
        return result.generations[0][0].text

    async def ainvoke(self, input: str, config: RunnableConfig | None = None,  # noqa: A002,A003
                      *, stop: list[str] | None = None, **kwargs: Any) -> str:
        return await asyncio.to_thread(self.invoke, input, config, stop=stop, **kwargs)

    def generate(self, prompts: list[str], *, stop: list[str] | None = None,
                 **kwargs: Any) -> LLMResult:
        results = [self._generate_with_cache(p, stop, **kwargs) for p in prompts]
        return LLMResult(generations=[g for r in results for g in r.generations],
                         llm_output={"model_name": self._llm_type})


class BaseChatModel(_SerializableBase, Runnable[Any, AIMessage]):
    """The chat model contract (upstream chat_models.py:325).

    Imperative: invoke / generate / stream. Declarative: bind_tools /
    with_structured_output / with_retry / with_fallbacks. Subclass surface:
    `_generate` + `_llm_type` required; `_stream` optional.
    """

    rate_limiter: BaseRateLimiter | None = None
    cache: BaseCache | None = None
    profile: ModelProfile | None = None

    @property
    @abstractmethod
    def _llm_type(self) -> str: ...

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {}

    def _llm_string(self) -> str:
        return f"{type(self).__name__}:{self._llm_type}:{sorted(self._identifying_params.items())}"

    @abstractmethod
    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None,
                  **kwargs: Any) -> ChatResult: ...

    def _stream(self, messages: list[BaseMessage], stop: list[str] | None = None,  # noqa: ARG002
                **kwargs: Any) -> Iterator[AIMessageChunk]:
        """Default streaming: one chunk carrying the whole generation."""
        result = self._generate(messages, stop=stop, **kwargs)
        msg = result.generations[0].message
        yield AIMessageChunk(id=msg.id, content=msg.content,
                             additional_kwargs=msg.additional_kwargs,
                             response_metadata=msg.response_metadata,
                             tool_calls=msg.tool_calls,
                             usage_metadata=msg.usage_metadata)

    # -- imperative surface --------------------------------------------------

    def _generate_with_cache(self, messages: list[BaseMessage], stop: list[str] | None,
                             **kwargs: Any) -> ChatResult:
        cache = self.cache
        if cache is not None:
            key_prompt = json.dumps([[m.type, m.content] for m in messages], default=str)
            hit = cache.lookup(key_prompt, self._llm_string())
            if hit is not None:
                return hit
        if self.rate_limiter is not None:
            self.rate_limiter.acquire()
        result = self._generate(messages, stop=stop, **kwargs)
        if cache is not None:
            key_prompt = json.dumps([[m.type, m.content] for m in messages], default=str)
            cache.update(key_prompt, self._llm_string(), result)
        return result

    def generate(self, messages_list: list[list[BaseMessage]],
                 stop: list[str] | None = None, **kwargs: Any) -> ChatResult:
        results = [self._generate_with_cache(list(messages), stop, **kwargs)
                   for messages in messages_list]
        return ChatResult(
            generations=[g for r in results for g in r.generations],
            llm_output={"model_name": self._llm_type},
        )

    def generate_prompt(self, prompts: list[PromptValue], stop: list[str] | None = None,
                        **kwargs: Any) -> ChatResult:
        return self.generate([p.to_messages() for p in prompts], stop=stop, **kwargs)

    def invoke(self, input: str | list[Any] | PromptValue,  # noqa: A002,A003
               config: RunnableConfig | None = None,
               *, stop: list[str] | None = None, **kwargs: Any) -> AIMessage:
        cfg = ensure_config(config)
        kwargs = {**cfg.get("kwargs", {}), **kwargs}
        messages = _convert_to_messages(input)
        result = self._generate_with_cache(messages, stop, **kwargs)
        return result.generations[0].message

    async def ainvoke(self, input: str | list[Any] | PromptValue,  # noqa: A002,A003
                      config: RunnableConfig | None = None,
                      *, stop: list[str] | None = None, **kwargs: Any) -> AIMessage:
        return await asyncio.to_thread(self.invoke, input, config, stop=stop, **kwargs)

    def stream(self, input: str | list[Any] | PromptValue,  # noqa: A002,A003
               config: RunnableConfig | None = None,
               *, stop: list[str] | None = None, **kwargs: Any) -> Iterator[AIMessageChunk]:
        cfg = ensure_config(config)
        kwargs = {**cfg.get("kwargs", {}), **kwargs}
        messages = _convert_to_messages(input)
        yield from self._stream(messages, stop=stop, **kwargs)

    async def astream(self, input: str | list[Any] | PromptValue,  # noqa: A002,A003
                      config: RunnableConfig | None = None,
                      *, stop: list[str] | None = None, **kwargs: Any):
        for chunk in self.stream(input, config, stop=stop, **kwargs):
            yield chunk

    # -- declarative surface -------------------------------------------------

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable:  # noqa: ARG002
        raise NotImplementedError(
            f"{type(self).__name__} does not support bind_tools; implement the "
            "provider tool-call wire format or use with_structured_output")

    def with_structured_output(self, schema: type[BaseModel] | dict[str, Any],
                               **kwargs: Any) -> Runnable:
        """Schema-into-prompt + JSON-out parser (the provider-agnostic fallback lane).

        Providers with native JSON mode override this; the fallback works with any
        model that can follow an instruction (and with the fake models in tests).
        """
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            schema_json = json.dumps(schema.model_json_schema(), indent=2)
            name = schema.__name__

            def _parse(text: str) -> BaseModel:
                stripped = text.strip()
                if stripped.startswith("```"):
                    stripped = stripped.strip("`")
                    if stripped.startswith("json"):
                        stripped = stripped[4:]
                data = json.loads(stripped)
                return schema.model_validate(data)  # type: ignore[union-attr]
        else:
            schema_json = json.dumps(schema, indent=2)
            name = "Result"

            def _parse(text: str) -> dict[str, Any]:
                return json.loads(text.strip().strip("`").removeprefix("json"))

        instruction = (
            f"Return ONLY a JSON object named {name} matching this JSON schema, "
            f"with no other text:\n{schema_json}"
        )

        parent = self

        class _Structured(Runnable):
            def invoke(self, input_value: str | list[Any] | PromptValue,  # noqa: A002,A003
                       config: RunnableConfig | None = None):
                messages = _convert_to_messages(input_value)
                if messages and isinstance(messages[0], SystemMessage):
                    messages[0] = SystemMessage(
                        content=f"{messages[0].content}\n\n{instruction}")
                else:
                    messages.insert(0, SystemMessage(content=instruction))
                out = parent.invoke(messages, config, **kwargs)
                return _parse(out.text)

        return _Structured()


# ---------------------------------------------------------------------------
# deterministic fakes for the suites (upstream fake_chat_models.py)
# ---------------------------------------------------------------------------


class FakeListChatModel(BaseChatModel):
    responses: list[str]
    idx: int = 0
    cycle: bool = True
    sleep_s: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "fake-list-chat"

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None,  # noqa: ARG002
                  **kwargs: Any) -> ChatResult:
        if self.sleep_s:
            time.sleep(self.sleep_s)
        text = self.responses[self.idx]
        if self.cycle:
            self.idx = (self.idx + 1) % len(self.responses)
        else:
            self.idx = min(self.idx + 1, len(self.responses) - 1)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def _stream(self, messages: list[BaseMessage], stop: list[str] | None = None,  # noqa: ARG002
                **kwargs: Any) -> Iterator[AIMessageChunk]:
        text = self.responses[self.idx]
        if self.cycle:
            self.idx = (self.idx + 1) % len(self.responses)
        for i in range(0, len(text), 3):
            yield AIMessageChunk(content=text[i:i + 3])


class FakeListLLM(BaseLLM):
    responses: list[str]
    idx: int = 0

    @property
    def _llm_type(self) -> str:
        return "fake-list-llm"

    def _generate(self, prompts: list[str], stop: list[str] | None = None,  # noqa: ARG002
                  **kwargs: Any) -> LLMResult:
        text = self.responses[self.idx]
        self.idx = (self.idx + 1) % len(self.responses)
        return LLMResult(generations=[[Generation(text=text)]])
