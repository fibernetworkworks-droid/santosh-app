"""HOOLA AEP parsers - output parsers as Runnables, the langchain-core
`output_parsers/` idea hand-built (upstream reference: output_parsers/base.py,
string.py, json.py, pydantic.py).

v0.510.0 HOOLA CORE: parse model text into structured values; `| model | parser`
just works because parsers are Runnables. JsonOutputParser tolerates fenced code
blocks; PydanticOutputParser validates into the model and ships format
instructions embedding the JSON schema. Inert library.
"""
from __future__ import annotations

import json
from abc import abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from .messages import BaseMessage
from .runnable import Runnable, RunnableConfig, RunnableSerializable

T = TypeVar("T")


class BaseOutputParser(RunnableSerializable[Any, T], Generic[T]):
    """Parse raw model output (str or BaseMessage) into a typed value."""

    @abstractmethod
    def parse(self, text: str) -> T: ...

    def parse_result(self, result: Any) -> T:
        if isinstance(result, BaseMessage):
            return self.parse(result.text)
        if isinstance(result, str):
            return self.parse(result)
        raise TypeError(f"Unsupported parser input: {type(result).__name__}")

    def parse_with_prompt(self, text: str, prompt: Any) -> T:  # noqa: ARG002 - prompt-aware hook
        return self.parse(text)

    def invoke(self, input: Any, config: RunnableConfig | None = None) -> T:  # noqa: A002,A003
        return self.parse_result(input)

    def get_format_instructions(self) -> str:
        return ""


class StrOutputParser(BaseOutputParser[str]):
    def parse(self, text: str) -> str:
        return text

    def parse_result(self, result: Any) -> str:
        if isinstance(result, BaseMessage):
            return result.text
        if isinstance(result, str):
            return result
        raise TypeError(f"Unsupported parser input: {type(result).__name__}")


def _strip_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:]
    return stripped.strip()


class JsonOutputParser(BaseOutputParser[Any]):
    """Parse JSON from raw or fenced output; a parse failure raises with the text."""

    def parse(self, text: str) -> Any:
        try:
            return json.loads(_strip_fence(text))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON output: {e}\nGot: {text[:200]}") from e

    def get_format_instructions(self) -> str:
        return ("Return ONLY a valid JSON object. No prose, no markdown fences "
                "unless asked.")


class PydanticOutputParser(BaseOutputParser[BaseModel]):
    """Validate JSON into a pydantic model (upstream pydantic.py)."""

    pydantic_object: type[BaseModel]

    def parse(self, text: str) -> BaseModel:
        try:
            data = json.loads(_strip_fence(text))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for {self.pydantic_object.__name__}: {e}") from e
        return self.pydantic_object.model_validate(data)

    def get_format_instructions(self) -> str:
        schema = json.dumps(self.pydantic_object.model_json_schema(), indent=2)
        return (f"The output should be a JSON object that validates against this "
                f"JSON schema:\n{schema}")
