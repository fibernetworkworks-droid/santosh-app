"""HOOLA AEP prompts - prompt templates as Runnables, the langchain-core
`prompts/` idea hand-built (upstream reference: prompts/base.py, prompt.py
PromptTemplate, chat.py:794 ChatPromptTemplate, :53 MessagesPlaceholder).

v0.510.0 HOOLA CORE: a prompt is a Runnable[dict, PromptValue]; string templates
format via str.format (f-string style), chat prompts take ("role", template) tuples
plus placeholders; partials freeze variables. Inert library.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any, Sequence

from pydantic import Field

from .messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from .runnable import Runnable, RunnableConfig, RunnableSerializable
from .serializable import Serializable


class PromptValue(Serializable):
    """The formatted prompt handed to a model."""

    def to_string(self) -> str:  # pragma: no cover - abstract by convention
        raise NotImplementedError

    @abstractmethod
    def to_messages(self) -> list[BaseMessage]: ...


class StringPromptValue(PromptValue):
    text: str

    def to_string(self) -> str:
        return self.text

    def to_messages(self) -> list[BaseMessage]:
        return [HumanMessage(content=self.text)]


class ChatPromptValue(PromptValue):
    messages: list[BaseMessage]

    def to_string(self) -> str:
        return "\n".join(m.pretty_repr() for m in self.messages)

    def to_messages(self) -> list[BaseMessage]:
        return list(self.messages)


class BasePromptTemplate(RunnableSerializable[dict[str, Any], PromptValue]):
    input_variables: list[str] = Field(default_factory=list)
    partial_variables: dict[str, Any] = Field(default_factory=dict)

    @abstractmethod
    def format_prompt(self, **kwargs: Any) -> PromptValue: ...

    def invoke(self, input: dict[str, Any], config: RunnableConfig | None = None) -> PromptValue:  # noqa: A002,A003
        merged = {**self.partial_variables, **(input or {})}
        return self.format_prompt(**merged)

    def partial(self, **kwargs: Any) -> "BasePromptTemplate":
        clone = self.model_copy(deep=True)
        clone.partial_variables = {**clone.partial_variables, **kwargs}
        clone.input_variables = [v for v in clone.input_variables if v not in kwargs]
        return clone


class PromptTemplate(BasePromptTemplate):
    """A string template with `{var}` slots (upstream prompt.py)."""

    template: str
    template_format: str = "f-string"

    @classmethod
    def from_template(cls, template: str, *, partial_variables: dict[str, Any] | None = None) \
            -> "PromptTemplate":
        import string
        vars_ = [fname for _, fname, _, _ in string.Formatter().parse(template) if fname]
        return cls(template=template, input_variables=sorted(set(vars_)),
                   partial_variables=partial_variables or {})

    def format(self, **kwargs: Any) -> str:
        merged = {**self.partial_variables, **kwargs}
        missing = [v for v in self.input_variables if v not in merged]
        if missing:
            raise KeyError(f"Missing template variables: {missing}")
        return self.template.format(**merged)

    def format_prompt(self, **kwargs: Any) -> PromptValue:
        return StringPromptValue(text=self.format(**kwargs))


class MessagesPlaceholder(Serializable):
    """A slot in a chat template filled with a message list (upstream chat.py:53)."""

    variable_name: str
    optional: bool = False

    def format_messages(self, kwargs: dict[str, Any]) -> list[BaseMessage]:
        if self.variable_name not in kwargs:
            if self.optional:
                return []
            raise KeyError(f"Missing placeholder variable: {self.variable_name}")
        value = kwargs[self.variable_name]
        out: list[BaseMessage] = []
        for m in value if isinstance(value, (list, tuple)) else [value]:
            if isinstance(m, BaseMessage):
                out.append(m)
            elif isinstance(m, str):
                out.append(HumanMessage(content=m))
            elif isinstance(m, dict):
                role = m.get("role", "human")
                cls = {"human": HumanMessage, "user": HumanMessage,
                       "ai": AIMessage, "assistant": AIMessage,
                       "system": SystemMessage}.get(role)
                out.append(cls(content=m.get("content", "")) if cls
                           else HumanMessage(content=m.get("content", "")))
        return out


_ROLE_CLASSES: dict[str, type[BaseMessage]] = {
    "system": SystemMessage, "human": HumanMessage, "user": HumanMessage,
    "ai": AIMessage, "assistant": AIMessage,
}


class _StringMessageTemplate(Serializable):
    role: str
    template: str

    def format_messages(self, kwargs: dict[str, Any]) -> list[BaseMessage]:
        import string
        vars_ = [f for _, f, _, _ in string.Formatter().parse(self.template) if f]
        missing = [v for v in vars_ if v not in kwargs]
        if missing:
            raise KeyError(f"Missing message variables: {missing}")
        text = self.template.format(**kwargs)
        cls = _ROLE_CLASSES.get(self.role)
        if cls is None:
            from .messages import ChatMessage
            return [ChatMessage(role=self.role, content=text)]
        return [cls(content=text)]


class ChatPromptTemplate(BasePromptTemplate):
    """A chat prompt from ("role", template) tuples + placeholders (upstream chat.py:794)."""

    messages: list[Any]

    @classmethod
    def from_messages(cls, messages: Sequence[Any]) -> "ChatPromptTemplate":
        coerced: list[Any] = []
        for m in messages:
            if isinstance(m, MessagesPlaceholder):
                coerced.append(m)
            elif isinstance(m, BaseMessage):
                coerced.append(_StringMessageTemplate(role=m.type, template=m.text))
            elif isinstance(m, (tuple, list)) and len(m) == 2:
                role, template = m
                if role == "placeholder":
                    coerced.append(MessagesPlaceholder(variable_name=template))
                else:
                    coerced.append(_StringMessageTemplate(role=role, template=template))
            else:
                raise TypeError(f"Unsupported prompt message spec: {type(m).__name__}")
        return cls(messages=coerced)

    @property
    def input_variables(self) -> list[str]:  # type: ignore[override]
        vars_: list[str] = []
        for m in self.messages:
            if isinstance(m, MessagesPlaceholder):
                vars_.append(m.variable_name)
            elif isinstance(m, _StringMessageTemplate):
                import string
                vars_.extend(f for _, f, _, _ in string.Formatter().parse(m.template) if f)
        ordered = list(dict.fromkeys(vars_))
        return [v for v in ordered if v not in self.partial_variables]

    def format_messages(self, **kwargs: Any) -> list[BaseMessage]:
        merged = {**self.partial_variables, **kwargs}
        out: list[BaseMessage] = []
        for m in self.messages:
            out.extend(m.format_messages(merged))
        return out

    def format_prompt(self, **kwargs: Any) -> PromptValue:
        return ChatPromptValue(messages=self.format_messages(**kwargs))

    def __add__(self, other: "ChatPromptTemplate") -> "ChatPromptTemplate":
        if not isinstance(other, ChatPromptTemplate):
            return NotImplemented
        return ChatPromptTemplate(messages=[*self.messages, *other.messages])
