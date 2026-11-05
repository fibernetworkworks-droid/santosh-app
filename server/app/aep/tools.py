"""HOOLA AEP tools - the tool layer, the langchain-core `tools/` idea hand-built
(upstream reference: tools/base.py:433 BaseTool, :459 ChildTool, tools/convert.py the
@tool decorator, tools/structured.py StructuredTool).

v0.510.0 HOOLA CORE: a tool is a Runnable whose input is a str, an args dict or a
tool_call dict (which round-trips to a ToolMessage). `@tool` infers the args schema
from type hints + the docstring's Args section (pydantic create_model - never eval);
injected args (context/tenant handles) are excluded from the model-facing
tool_call_schema, the docs7/skills_tool law upstream names InjectedToolArg. Inert
library: a tool runs only when invoked.
"""
from __future__ import annotations

import inspect
from abc import abstractmethod
from typing import Any, Callable, Literal, Type, get_args, get_origin, get_type_hints

from pydantic import BaseModel, ConfigDict, Field, create_model

from .messages import ToolMessage, ToolCall
from .runnable import Runnable, RunnableConfig, RunnableSerializable


class ToolException(Exception):
    """Raised when a tool fails on user input (upstream tools/base.py:371)."""


class InjectedToolArg:
    """Annotation marker: excluded from the model-facing schema, filled by the house."""


def _is_injected(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is not None:
        return any(_is_injected(a) for a in get_args(annotation))
    return annotation is InjectedToolArg or (
        isinstance(annotation, type) and issubclass(annotation, InjectedToolArg)
    )


def _parse_docstring_args(fn: Callable) -> dict[str, str]:
    """Google-style `Args:` section -> {param: description} (upstream _parse_python_function_docstring)."""
    doc = inspect.getdoc(fn) or ""
    out: dict[str, str] = {}
    in_args = False
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped.rstrip(":") == "Args":
            in_args = True
            continue
        if in_args:
            if not stripped:
                continue
            if ":" in stripped and (line.startswith("    ") or not stripped.startswith(("Returns", "Raises"))):
                name, _, desc = stripped.partition(":")
                if name.split()[0].isidentifier():
                    out[name.split()[0]] = desc.strip()
                continue
            if not line.startswith(" ") and stripped:
                break
    return out


def create_schema_from_function(name: str, fn: Callable) -> Type[BaseModel]:
    """Build a pydantic args model from a function's hints + docstring."""
    hints = get_type_hints(fn)
    sig = inspect.signature(fn)
    doc_args = _parse_docstring_args(fn)
    fields: dict[str, tuple[Any, Any]] = {}
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls") or param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        ann = hints.get(pname, param.annotation)
        if param.annotation is not inspect.Parameter.empty and _is_injected(param.annotation):
            continue
        if ann is inspect.Parameter.empty:
            ann = Any
        default = ... if param.default is inspect.Parameter.empty else param.default
        desc = doc_args.get(pname)
        fields[pname] = (ann, Field(default=default, description=desc))
    return create_model(f"{name}Args", **fields)


def _config_dict() -> ConfigDict:
    return ConfigDict(arbitrary_types_allowed=True)


class BaseTool(RunnableSerializable[Any, Any]):
    """A tool: name + description + args schema + the callable body."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"
    handle_tool_error: bool | str = False

    @classmethod
    def lc_id(cls) -> tuple[str, ...]:
        return ("aep", "tools", cls.__name__)

    @property
    def args(self) -> dict[str, Any]:
        schema = self.args_schema
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema.model_json_schema().get("properties", {})
        return {}

    @property
    def args_schema(self) -> Type[BaseModel] | dict[str, Any] | None:
        return None

    @property
    def tool_call_schema(self) -> Type[BaseModel] | dict[str, Any] | None:
        """The schema the MODEL sees - injected args excluded."""
        return self.args_schema

    @property
    def is_single_input(self) -> bool:
        props = self.args if isinstance(self.args, dict) else {}
        return len(props) <= 1

    @abstractmethod
    def _run(self, *args: Any, **kwargs: Any) -> Any: ...

    def _artifact(self, content: Any) -> Any:  # noqa: ARG002 - override for content_and_artifact
        return None

    def _parse_input(self, raw: Any) -> dict[str, Any] | str:
        if isinstance(raw, str):
            return raw
        if isinstance(raw, dict):
            if raw.get("type") == "tool_call" or ("name" in raw and "args" in raw and "id" in raw):
                args = raw.get("args") or {}
                if not isinstance(args, dict):
                    args = {"__args__": args}
                return args
            return raw
        raise ToolException(f"Unsupported tool input type: {type(raw).__name__}")

    def _invoke_bare(self, input: Any) -> Any:  # noqa: A002,A003
        parsed = self._parse_input(input)
        as_tool_call = isinstance(input, dict) and (
            input.get("type") == "tool_call" or ("name" in input and "args" in input and "id" in input)
        )
        try:
            if isinstance(parsed, str):
                result = self._run(parsed)
            else:
                result = self._run(**parsed)
        except ToolException as e:
            if self.handle_tool_error is False:
                raise
            content = self.handle_tool_error if isinstance(self.handle_tool_error, str) \
                else f"Tool error: {e}"
            result, errored = content, True
        else:
            errored = False
        if as_tool_call:
            call = input  # type: ignore[assignment]
            if errored:
                # the P7 lesson (McpTool is the first content_and_artifact tool
                # with handle_tool_error): an error result is a plain string -
                # indexing it would land a single character as the content
                content = result
            else:
                content = result[0] if self.response_format == "content_and_artifact" else result
            return ToolMessage(content=_stringify(content), tool_call_id=call.get("id") or "",
                               status="error" if errored else "success")
        if self.response_format == "content_and_artifact" and isinstance(result, tuple):
            return result[0]
        return result

    def invoke(self, input: Any, config: RunnableConfig | None = None) -> Any:  # noqa: A002,A003
        from .runnable import ensure_config as _ensure
        cfg = _ensure(config)
        if not cfg.get("callbacks"):
            return self._invoke_bare(input)
        from .tracers import Span
        span = Span.start(cfg, self, "tool", input)
        try:
            out = self._invoke_bare(input)
        except Exception as e:  # noqa: BLE001 - re-raised after the error event
            span.error(e)
            raise
        span.end(out)
        return out

    async def ainvoke(self, input: Any, config: RunnableConfig | None = None) -> Any:  # noqa: A002,A003
        import asyncio
        return await asyncio.to_thread(self.invoke, input, config)


def _stringify(content: Any) -> str:
    if isinstance(content, str):
        return content
    import json
    try:
        return json.dumps(content, default=str)
    except TypeError:
        return str(content)


class StructuredTool(BaseTool):
    """A tool built from an explicit function + schema (upstream structured.py)."""

    func: Callable[..., Any]
    coroutine: Callable[..., Any] | None = None
    args_schema_type: Type[BaseModel] | None = None

    @classmethod
    def from_function(cls, func: Callable, name: str | None = None,
                      description: str | None = None,
                      args_schema: Type[BaseModel] | None = None,
                      response_format: Literal["content", "content_and_artifact"] = "content") \
            -> "StructuredTool":
        if args_schema is None:
            args_schema = create_schema_from_function(name or func.__name__, func)
        doc = inspect.getdoc(func) or ""
        return cls(name=name or func.__name__, description=description or doc.split("\n")[0],
                   func=func, args_schema_type=args_schema, response_format=response_format)

    @property
    def args_schema(self) -> Type[BaseModel] | None:  # type: ignore[override]
        return self.args_schema_type

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)

    async def ainvoke(self, input: Any, config: RunnableConfig | None = None) -> Any:  # noqa: A002,A003
        import asyncio
        if self.coroutine is not None:
            parsed = self._parse_input(input)
            if isinstance(parsed, str):
                out = await self.coroutine(parsed)
            else:
                out = await self.coroutine(**parsed)
            if isinstance(input, dict) and (input.get("type") == "tool_call"):
                return ToolMessage(content=_stringify(out), tool_call_id=input.get("id") or "")
            return out
        return await super().ainvoke(input, config)


class _ToolDecorator:
    """The @tool decorator: schema from hints, description from the docstring."""

    def __call__(self, fn: Callable | None = None, *, name: str | None = None,
                 description: str | None = None, return_direct: bool = False,
                 response_format: Literal["content", "content_and_artifact"] = "content",
                 parse_docstring: bool = True, infer_schema: bool = True) -> Any:  # noqa: ARG002
        def _wrap(f: Callable) -> StructuredTool:
            doc = inspect.getdoc(f) or ""
            desc = description or (doc.split("\n")[0] if doc else name or f.__name__)
            schema = create_schema_from_function(name or f.__name__, f) if infer_schema else None
            tool_obj = StructuredTool.from_function(
                f, name=name, description=desc, args_schema=schema,
                response_format=response_format)
            tool_obj.return_direct = return_direct
            return tool_obj

        if fn is None:
            return _wrap
        return _wrap(fn)


tool = _ToolDecorator()
"""`@tool` / `@tool(description=...)` - the upstream convert.py decorator."""


def tool_call(name: str, args: dict[str, Any], id: str | None = None, index: int = 0) -> ToolCall:  # noqa: A002
    return {"type": "tool_call", "id": id, "name": name, "args": args, "index": index}
