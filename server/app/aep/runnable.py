"""HOOLA AEP runnable - the composition substrate, the langchain-core
`runnables/` idea hand-built (upstream reference: runnables/base.py:134 Runnable ABC,
:3079 RunnableSequence, :3868 RunnableParallel, :4707 RunnableLambda, :6382
RunnableBinding, retry.py + fallbacks.py).

v0.510.0 HOOLA CORE: a unit of work with invoke / ainvoke / batch / abatch /
stream / astream, composable with `|` into sequences and dict literals into
parallels; every composed chain gets sync + async + batch + streaming for free.
`with_retry` and `with_fallbacks` wrap any Runnable (hand-rolled backoff - no
tenacity dependency). Inert library; batch uses bounded threads like upstream.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Generic, Iterator, Mapping, Type, TypedDict, TypeVar, Union

from pydantic import BaseModel, Field

from .serializable import Serializable

Input = TypeVar("Input")
Output = TypeVar("Output")
Other = TypeVar("Other")


class RunnableConfig(TypedDict, total=False):
    tags: list[str]
    metadata: dict[str, Any]
    run_name: str
    run_id: uuid.UUID
    max_concurrency: int
    callbacks: Any
    configurable: dict[str, Any]
    recursion_limit: int
    kwargs: dict[str, Any]  # the aep binding channel (bind_tools kwargs ride here)


def ensure_config(config: RunnableConfig | None = None) -> RunnableConfig:
    return {**config} if config else RunnableConfig()


class Runnable(ABC, Generic[Input, Output]):
    """A unit of work that can be invoked, batched, streamed and composed."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        # Runnable-typed fields (sequence steps, parallel children, bindings) validate
        # as any - composition is checked at runtime by _coerce, not by pydantic.
        from pydantic_core import core_schema
        return core_schema.any_schema()

    @abstractmethod
    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        ...

    async def ainvoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        return await asyncio.to_thread(self.invoke, input, ensure_config(config))

    def batch(self, inputs: list[Input], config: RunnableConfig | None = None, *,
              return_exceptions: bool = False) -> list[Output]:
        cfg = ensure_config(config)
        max_c = cfg.get("max_concurrency") or min(len(inputs), 8) or 1
        def _one(i: Input) -> Output | Exception:
            try:
                return self.invoke(i, {**cfg})
            except Exception as e:  # noqa: BLE001 - returned by contract
                return e
        with ThreadPoolExecutor(max_workers=max_c) as pool:
            results = list(pool.map(_one, inputs))
        if not return_exceptions and any(isinstance(r, Exception) for r in results):
            for r in results:
                if isinstance(r, Exception):
                    raise r
        return results  # type: ignore[return-value]

    async def abatch(self, inputs: list[Input], config: RunnableConfig | None = None, *,
                     return_exceptions: bool = False) -> list[Output]:
        cfg = ensure_config(config)
        outs: list[Output | Exception] = list(await asyncio.gather(
            *(self.ainvoke(i, {**cfg}) for i in inputs), return_exceptions=True))
        if not return_exceptions:
            for r in outs:
                if isinstance(r, Exception):
                    raise r
        return outs  # type: ignore[return-value]

    def stream(self, input: Input, config: RunnableConfig | None = None) -> Iterator[Output]:  # noqa: A002,A003
        yield self.invoke(input, config)

    async def astream(self, input: Input, config: RunnableConfig | None = None):  # noqa: A002,A003
        for chunk in self.stream(input, config):
            yield chunk

    def get_name(self, suffix: str | None = None) -> str:
        name = type(self).__name__
        return f"{name}{suffix}" if suffix else name

    def get_input_schema(self, config: RunnableConfig | None = None) -> dict[str, Any]:  # noqa: ARG002
        return {"title": self.get_name(), "type": "object"}

    def get_output_schema(self, config: RunnableConfig | None = None) -> dict[str, Any]:  # noqa: ARG002
        return {"title": self.get_name(), "type": "object"}

    # -- composition ---------------------------------------------------------

    def pipe(self, other: Any) -> "RunnableSequence":
        return RunnableSequence(self, _coerce(other))

    def __or__(self, other: Any) -> "RunnableSequence":
        return self.pipe(other)

    def __ror__(self, other: Any) -> "RunnableSequence":
        return RunnableSequence(_coerce(other), self)

    # -- wrappers ------------------------------------------------------------

    def with_retry(self, *, stop_after_attempt: int = 3, wait_seconds: float = 0.1) -> "RunnableRetry":
        return RunnableRetry(retryable=self, stop_after_attempt=stop_after_attempt,
                             wait_seconds=wait_seconds)

    def with_fallbacks(self, fallbacks: "list[Runnable[Input, Output]]",
                       *, exceptions_to_handle: tuple[Type[Exception], ...] = (Exception,)) \
            -> "RunnableWithFallbacks":
        return RunnableWithFallbacks(runnable=self, fallbacks=list(fallbacks),
                                     exceptions_to_handle=exceptions_to_handle)


def _coerce(other: Any) -> Runnable:
    """Coerce the right side of `|` into a Runnable (upstream base.py coercion)."""
    if isinstance(other, Runnable):
        return other
    if callable(other):
        return RunnableLambda(other)
    if isinstance(other, dict):
        return RunnableParallel(other)
    return RunnablePassthrough()


class RunnableSerializable(Serializable, Runnable[Input, Output]):
    """A Runnable that also serializes (the upstream RunnableSerializable)."""


class RunnableSequence(RunnableSerializable[Input, Output]):
    """Run steps left to right; one step's output is the next's input."""

    first: Runnable
    middle: list[Runnable] = Field(default_factory=list)
    last: Runnable

    def __init__(self, first: Runnable, last: Runnable, middle: list[Runnable] | None = None,
                 **kwargs: Any) -> None:
        middle = middle or []
        super().__init__(first=first, middle=middle, last=last, **kwargs)

    @classmethod
    def from_steps(cls, steps: list[Runnable]) -> "RunnableSequence":
        if len(steps) < 2:
            raise ValueError("RunnableSequence needs at least two steps")
        return cls(steps[0], steps[-1], middle=list(steps[1:-1]))

    @property
    def steps(self) -> list[Runnable]:
        return [self.first, *self.middle, self.last]

    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        cfg = ensure_config(config)
        out: Any = input
        for step in self.steps:
            out = step.invoke(out, {**cfg})
        return out  # type: ignore[return-value]

    async def ainvoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        cfg = ensure_config(config)
        out: Any = input
        for step in self.steps:
            out = await step.ainvoke(out, {**cfg})
        return out  # type: ignore[return-value]

    def stream(self, input: Input, config: RunnableConfig | None = None):  # noqa: A002,A003
        cfg = ensure_config(config)
        # pure-sync chain: each step streams over the previous step's chunks
        def _chain(gen, step):
            for acc in gen:
                yield from step.stream(acc, {**cfg})
        gen = self.first.stream(input, {**cfg})
        for step in self.middle + [self.last]:
            gen = _chain(gen, step)
        yield from gen

    def get_input_schema(self, config: RunnableConfig | None = None) -> dict[str, Any]:
        return self.first.get_input_schema(config)


async def _stream_handoff(step: Runnable, gen, cfg):
    async for acc in _iter_stream(gen):
        async for chunk in step.astream(acc, cfg):
            yield chunk


def _iter_stream(gen):
    """Iterate a sync or async generator uniformly."""
    import inspect
    if inspect.isasyncgen(gen):
        return gen
    async def _wrap():
        for item in gen:
            yield item
    return _wrap()


class RunnableParallel(RunnableSerializable[Input, dict[str, Any]]):
    """Run the same input through every child concurrently; outputs keyed by name."""

    steps: dict[str, Runnable]

    def __init__(self, steps: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        coerced = {k: _coerce(v) for k, v in {**(steps or {}), **kwargs}.items()}
        super().__init__(steps=coerced)

    def invoke(self, input: Input, config: RunnableConfig | None = None) -> dict[str, Any]:  # noqa: A002,A003
        cfg = ensure_config(config)
        if not self.steps:
            return {}
        if len(self.steps) == 1:
            [(k, v)] = self.steps.items()
            return {k: v.invoke(input, {**cfg})}
        with ThreadPoolExecutor(max_workers=len(self.steps)) as pool:
            futures = {k: pool.submit(v.invoke, input, {**cfg}) for k, v in self.steps.items()}
            return {k: f.result() for k, f in futures.items()}

    async def ainvoke(self, input: Input, config: RunnableConfig | None = None) -> dict[str, Any]:  # noqa: A002,A003
        cfg = ensure_config(config)
        values = await asyncio.gather(*(v.ainvoke(input, {**cfg}) for v in self.steps.values()))
        return dict(zip(self.steps.keys(), values))


class RunnableLambda(Runnable[Input, Output]):
    """Wrap any callable; sync and async variants, streaming yields per chunk."""

    fn: Callable[..., Output]
    afn: Callable[..., Any] | None = None
    name: str | None = None

    def __init__(self, fn: Callable[..., Output], afn: Callable[..., Any] | None = None,
                 name: str | None = None) -> None:
        import inspect
        if inspect.iscoroutinefunction(fn):
            # an async function alone is legal - invoke() will refuse, ainvoke() works
            afn = fn
            fn = _async_only(fn)  # type: ignore[assignment]
        self.fn = fn
        self.afn = afn
        self.name = name

    def get_name(self, suffix: str | None = None) -> str:
        base = self.name or getattr(self.fn, "__name__", None) or "RunnableLambda"
        return f"{base}{suffix}" if suffix else base

    def get_input_schema(self, config: RunnableConfig | None = None) -> dict[str, Any]:
        import inspect
        try:
            sig = inspect.signature(self.fn)
            first = next(iter(sig.parameters.values()))
            ann = first.annotation
            if isinstance(ann, type) and issubclass(ann, BaseModel):
                return ann.model_json_schema()
        except (ValueError, StopIteration, TypeError):
            pass
        return {"title": self.get_name(), "type": "object"}

    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        if getattr(self.fn, "_aep_async_only", False):
            raise TypeError("RunnableLambda(fn) is async-only; use ainvoke")
        return self.fn(input)

    async def ainvoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        if self.afn is not None:
            return await self.afn(input)
        return await asyncio.to_thread(self.fn, input)


def _async_only(afn):
    def _shim(*a, **k):
        raise TypeError("RunnableLambda(fn) is async-only; use ainvoke")
    _shim._aep_async_only = True  # type: ignore[attr-defined]
    _shim.__name__ = getattr(afn, "__name__", "async_fn")
    return _shim


class RunnablePassthrough(RunnableSerializable[Input, Input]):
    """Identity - returns its input unchanged (extra kwargs merge dicts for prompts)."""

    extra: dict[str, Any] = Field(default_factory=dict)

    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Input:  # noqa: A002,A003
        if isinstance(input, dict) and self.extra:
            return {**self.extra, **input}  # type: ignore[return-value]
        return input

    @classmethod
    def assign(cls, **kwargs: Any) -> "RunnableParallel":
        return RunnableParallel(kwargs)


class RunnableBinding(RunnableSerializable[Input, Output]):
    """A Runnable with kwargs permanently bound into the config binding channel."""

    bound: Runnable
    kwargs: dict[str, Any] = Field(default_factory=dict)

    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        cfg = ensure_config(config)
        merged_kwargs = {**self.kwargs, **cfg.get("kwargs", {})}
        return self.bound.invoke(input, {**cfg, "kwargs": merged_kwargs})  # type: ignore[typeddict-item]

    async def ainvoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        cfg = ensure_config(config)
        merged_kwargs = {**self.kwargs, **cfg.get("kwargs", {})}
        return await self.bound.ainvoke(input, {**cfg, "kwargs": merged_kwargs})  # type: ignore[typeddict-item]

    def bind(self, **kwargs: Any) -> "RunnableBinding":
        return RunnableBinding(bound=self, kwargs=kwargs)  # type: ignore[arg-type,return-value]

    def get_name(self, suffix: str | None = None) -> str:
        return self.bound.get_name(suffix)


class RunnableRetry(RunnableSerializable[Input, Output]):
    """Retry a Runnable with linear backoff (the hand-rolled with_retry)."""

    retryable: Runnable
    stop_after_attempt: int = 3
    wait_seconds: float = 0.1

    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        last: Exception | None = None
        for attempt in range(1, self.stop_after_attempt + 1):
            try:
                return self.retryable.invoke(input, config)
            except Exception as e:  # noqa: BLE001 - retry by contract
                last = e
                if attempt < self.stop_after_attempt and self.wait_seconds:
                    time.sleep(self.wait_seconds * attempt)
        raise last  # type: ignore[misc]

    async def ainvoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        last: Exception | None = None
        for attempt in range(1, self.stop_after_attempt + 1):
            try:
                return await self.retryable.ainvoke(input, config)
            except Exception as e:  # noqa: BLE001 - retry by contract
                last = e
                if attempt < self.stop_after_attempt and self.wait_seconds:
                    await asyncio.sleep(self.wait_seconds * attempt)
        raise last  # type: ignore[misc]


class RunnableWithFallbacks(RunnableSerializable[Input, Output]):
    """Try the primary, then each fallback in order; raise the last error if all fail."""

    runnable: Runnable
    fallbacks: list[Runnable] = Field(default_factory=list)
    exceptions_to_handle: tuple[Type[Exception], ...] = (Exception,)

    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        candidates = [self.runnable, *self.fallbacks]
        last: Exception | None = None
        for candidate in candidates:
            try:
                return candidate.invoke(input, config)
            except self.exceptions_to_handle as e:  # noqa: PERF203 - ordered attempts
                last = e
        raise last  # type: ignore[misc]

    async def ainvoke(self, input: Input, config: RunnableConfig | None = None) -> Output:  # noqa: A002,A003
        candidates = [self.runnable, *self.fallbacks]
        last: Exception | None = None
        for candidate in candidates:
            try:
                return await candidate.ainvoke(input, config)
            except self.exceptions_to_handle as e:  # noqa: PERF203
                last = e
        raise last  # type: ignore[misc]


LanguageModelLike = Union[Any, "Runnable"]
