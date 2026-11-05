"""HOOLA AEP messages - the message data model, the langchain-core
`messages/` idea hand-built (upstream reference: libs/core/langchain_core/messages/base.py:93
BaseMessage, content.py's 17 TypedDict content blocks, ai.py AIMessageChunk merging).

v0.510.0 HOOLA CORE: one canonical message shape for every brain Hoola talks to.
`content` stays the forgiving `str | list` channel; `content_blocks` is the typed
standard channel (text / tool_call / server tools / reasoning / refusal / media /
citation / non_standard). Voice transcripts ride AudioContentBlock -> text; docs7
rows surface as Citation blocks; provider chaos gets normalized into this one shape
(the upstream block_translators contract). Inert library: no network, no threads.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict, Union

from pydantic import Field

from .serializable import Serializable

# ---------------------------------------------------------------------------
# The standard content-block vocabulary - 17 TypedDicts, the upstream
# messages/content.py shape (class list read at content.py:126-817).
# ---------------------------------------------------------------------------


class Citation(TypedDict, total=False):
    type: Literal["citation"]
    id: str
    source_id: str
    url: str
    title: str
    start_index: int
    end_index: int
    cited_text: str
    extras: dict[str, Any]


class NonStandardAnnotation(TypedDict, total=False):
    type: Literal["non_standard_annotation"]
    id: str
    value: dict[str, Any]


class TextContentBlock(TypedDict, total=False):
    type: Literal["text"]
    id: str
    text: str
    annotations: list[Union[Citation, NonStandardAnnotation]]
    index: int
    extras: dict[str, Any]


class _ToolCallCore(TypedDict):
    type: Literal["tool_call"]
    id: str | None
    name: str
    args: dict[str, Any]


class ToolCall(_ToolCallCore, total=False):
    index: int
    extras: dict[str, Any]


class ToolCallChunk(TypedDict, total=False):
    type: Literal["tool_call_chunk"]
    id: str | None
    name: str | None
    args: str | None
    index: int
    extras: dict[str, Any]


class InvalidToolCall(TypedDict, total=False):
    type: Literal["invalid_tool_call"]
    id: str | None
    name: str | None
    args: str | None
    error: str | None
    index: int
    extras: dict[str, Any]


class ServerToolCall(TypedDict, total=False):
    type: Literal["server_tool_call"]
    id: str
    name: str
    args: dict[str, Any]
    index: int
    extras: dict[str, Any]


class ServerToolCallChunk(TypedDict, total=False):
    type: Literal["server_tool_call_chunk"]
    id: str
    name: str
    args: str
    index: int
    extras: dict[str, Any]


class ServerToolResult(TypedDict, total=False):
    type: Literal["server_tool_result"]
    id: str
    tool_call_id: str
    status: Literal["success", "error"]
    content: Any
    index: int
    extras: dict[str, Any]


class ReasoningContentBlock(TypedDict, total=False):
    type: Literal["reasoning"]
    id: str
    reasoning: str
    index: int
    extras: dict[str, Any]


class RefusalContentBlock(TypedDict, total=False):
    type: Literal["refusal"]
    id: str
    refusal: str
    index: int
    extras: dict[str, Any]


class _MediaContentBlock(TypedDict, total=False):
    id: str
    base64: str
    url: str
    index: int
    extras: dict[str, Any]


class ImageContentBlock(_MediaContentBlock, total=False):
    type: Literal["image"]


class VideoContentBlock(_MediaContentBlock, total=False):
    type: Literal["video"]


class AudioContentBlock(_MediaContentBlock, total=False):
    type: Literal["audio"]


class PlainTextContentBlock(TypedDict, total=False):
    type: Literal["plain_text"]
    id: str
    plain_text: str
    index: int
    extras: dict[str, Any]


class FileContentBlock(_MediaContentBlock, total=False):
    type: Literal["file"]
    filename: str
    mime_type: str


class NonStandardContentBlock(TypedDict, total=False):
    type: Literal["non_standard"]
    id: str
    value: Any
    index: int
    extras: dict[str, Any]


CONTENT_BLOCK_TYPES: tuple[str, ...] = (
    "text", "tool_call", "tool_call_chunk", "invalid_tool_call",
    "server_tool_call", "server_tool_call_chunk", "server_tool_result",
    "reasoning", "refusal", "image", "video", "audio", "plain_text",
    "file", "citation", "non_standard_annotation", "non_standard",
)

ContentBlock = Union[
    TextContentBlock, ToolCall, ToolCallChunk, InvalidToolCall, ServerToolCall,
    ServerToolCallChunk, ServerToolResult, ReasoningContentBlock,
    RefusalContentBlock, ImageContentBlock, VideoContentBlock, AudioContentBlock,
    PlainTextContentBlock, FileContentBlock, Citation, NonStandardAnnotation,
    NonStandardContentBlock,
]

# ---------------------------------------------------------------------------
# merge helpers (upstream base.py:366 merge_content + utils merge_dicts)
# ---------------------------------------------------------------------------


def merge_content(
    first: str | list[Any] | None, second: str | list[Any] | None
) -> str | list[Any]:
    """Merge two content payloads: strings concat, lists extend, mixed coerces to list."""
    if first is None:
        return second if second is not None else ""
    if second is None:
        return first
    if isinstance(first, str) and isinstance(second, str):
        return first + second
    first_list = [first] if isinstance(first, str) else list(first)
    second_list = [second] if isinstance(second, str) else list(second)
    return first_list + second_list


def merge_dicts(a: dict[Any, Any] | None, b: dict[Any, Any] | None) -> dict[Any, Any]:
    out = dict(a or {})
    for k, v in (b or {}).items():
        out[k] = merge_dicts(out.get(k), v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


# ---------------------------------------------------------------------------
# The message family (upstream base.py:93, ai.py, human.py, system.py,
# tool.py, chat.py, modifier.py RemoveMessage).
# ---------------------------------------------------------------------------


class BaseMessage(Serializable):
    """The unit of conversation: inputs and outputs of a chat model."""

    content: str | list[Any] = ""
    content_blocks: list[ContentBlock] | None = Field(
        default=None,
        description="The typed standard channel; when content is absent it is derived from these.",
    )
    additional_kwargs: dict[Any, Any] = Field(default_factory=dict)
    response_metadata: dict[Any, Any] = Field(default_factory=dict)
    type: str
    name: str | None = None
    id: str | None = None

    def __init__(self, content: str | list[Any] | None = None, **kwargs: Any) -> None:
        blocks = kwargs.get("content_blocks")
        if content is None and blocks is not None:
            content = list(blocks)
        if content is None:
            content = ""
        super().__init__(content=content, **kwargs)

    @property
    def text(self) -> str:
        """The plain-text view: a str content as-is, else the text/reasoning blocks joined."""
        if isinstance(self.content, str):
            return self.content
        parts: list[str] = []
        for block in self.content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif isinstance(block, dict) and isinstance(block.get("reasoning"), str):
                parts.append(block["reasoning"])
        return "".join(parts)

    def pretty_repr(self, html: bool = False) -> str:  # noqa: ARG002 - upstream parity
        return f"[{self.type}]: {self.text}"


class HumanMessage(BaseMessage):
    type: Literal["human"] = "human"


class AIMessage(BaseMessage):
    type: Literal["ai"] = "ai"
    tool_calls: list[ToolCall] = Field(default_factory=list)
    invalid_tool_calls: list[InvalidToolCall] = Field(default_factory=list)
    usage_metadata: dict[str, Any] | None = None


class SystemMessage(BaseMessage):
    type: Literal["system"] = "system"


class ChatMessage(BaseMessage):
    """A message with an arbitrary provider role; the role IS the message type."""

    def __init__(self, content: str | list[Any] | None = None, **kwargs: Any) -> None:
        role = kwargs.pop("role", None) or kwargs.get("type") or "user"
        kwargs.pop("type", None)
        super().__init__(content=content, type=role, **kwargs)


class ToolMessage(BaseMessage):
    type: Literal["tool"] = "tool"
    tool_call_id: str
    status: Literal["success", "error"] = "success"


class FunctionMessage(BaseMessage):
    """Legacy completion-calls shape, kept for the parity audit."""

    type: Literal["function"] = "function"
    name: str


REMOVE_ALL_MESSAGES = "remove_all"


class RemoveMessage(BaseMessage):
    """A tombstone that tells history reducers to drop a message id (upstream modifier.py)."""

    type: Literal["remove"] = "remove"
    id: str
    content: str | list[Any] = ""

    def __init__(self, id: str | None = None, **kwargs: Any) -> None:  # noqa: A002 - upstream name
        if id is None:
            id = kwargs.pop("id", REMOVE_ALL_MESSAGES)
        super().__init__(content="", id=id, **kwargs)


# ---------------------------------------------------------------------------
# Chunks (upstream ai.py AIMessageChunk + base.py:412 BaseMessageChunk)
# ---------------------------------------------------------------------------


class AIMessageChunk(AIMessage):
    """A streamed partial AIMessage; `+` merges chunks exactly like upstream."""

    tool_call_chunks: list[ToolCallChunk] = Field(default_factory=list)

    def __add__(self, other: Any) -> "AIMessageChunk":
        if isinstance(other, dict):
            other = AIMessageChunk(**other)
        if not isinstance(other, AIMessageChunk):
            return NotImplemented
        merged_tool_calls = _merge_tool_call_chunks(self.tool_call_chunks, other.tool_call_chunks)
        merged_calls: list[ToolCall] = []
        for tc in merged_tool_calls:
            try:
                import json as _json
                args = tc.get("args")
                parsed = _json.loads(args) if isinstance(args, str) and args else (args or {})
                merged_calls.append({"type": "tool_call", "id": tc.get("id"),
                                     "name": tc.get("name") or "", "args": parsed})
            except Exception:
                merged_calls.append({"type": "tool_call", "id": tc.get("id"),
                                     "name": tc.get("name") or "", "args": {}})
        return AIMessageChunk(
            id=self.id if self.id is not None else other.id,
            content=merge_content(self.content, other.content),
            additional_kwargs=merge_dicts(self.additional_kwargs, other.additional_kwargs),
            response_metadata=merge_dicts(self.response_metadata, other.response_metadata),
            tool_calls=merged_calls,
            tool_call_chunks=merged_tool_calls,
            usage_metadata=other.usage_metadata or self.usage_metadata,
        )

    @classmethod
    def from_chunks(cls, chunks: list["AIMessageChunk"]) -> "AIMessageChunk":
        out = cls(content="")
        for chunk in chunks:
            out = out + chunk
        return out


def _merge_tool_call_chunks(
    left: list[ToolCallChunk], right: list[ToolCallChunk]
) -> list[ToolCallChunk]:
    out: dict[int, ToolCallChunk] = {tc.get("index", i): dict(tc) for i, tc in enumerate(left)}
    for tc in right:
        idx = tc.get("index")
        if idx is None:
            out[max(out.keys(), default=-1) + 1] = dict(tc)
            continue
        if idx in out:
            cur = out[idx]
            out[idx] = {
                "type": "tool_call_chunk",
                "id": cur.get("id") or tc.get("id"),
                "name": (cur.get("name") or "") + (tc.get("name") or ""),
                "args": (cur.get("args") or "") + (tc.get("args") or ""),
                "index": idx,
            }
        else:
            out[idx] = dict(tc)
    return [out[k] for k in sorted(out)]


def message_chunk_to_message(chunk: BaseMessage) -> BaseMessage:
    """Downgrade a chunk to a plain message (drop chunk-only fields)."""
    data = {
        "content": chunk.content,
        "additional_kwargs": chunk.additional_kwargs,
        "response_metadata": chunk.response_metadata,
        "id": chunk.id,
        "name": chunk.name,
    }
    if isinstance(chunk, AIMessage):
        return AIMessage(tool_calls=chunk.tool_calls, usage_metadata=chunk.usage_metadata, **data)
    return BaseMessage(type=chunk.type, **data)


# ---------------------------------------------------------------------------
# dict round trip (upstream base.py:477 message_to_dict, :491 messages_to_dict)
# ---------------------------------------------------------------------------

_TYPES: dict[str, type[BaseMessage]] = {
    "human": HumanMessage, "ai": AIMessage, "system": SystemMessage,
    "tool": ToolMessage, "function": FunctionMessage, "remove": RemoveMessage,
}


def message_to_dict(message: BaseMessage) -> dict[str, Any]:
    return {
        "type": message.type,
        "data": message.model_dump(exclude={"type"}),
    }


def messages_to_dict(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    return [message_to_dict(m) for m in messages]


def messages_from_dict(messages: list[dict[str, Any]]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for m in messages:
        data = dict(m.get("data", {}))
        mtype = m.get("type") or data.get("type") or "human"
        cls = _TYPES.get(mtype, ChatMessage)
        data.pop("type", None)
        if cls is ChatMessage:
            out.append(ChatMessage(role=mtype, content=data.pop("content", ""), **data))
        else:
            out.append(cls(**data))
    return out


def get_msg_title_repr(title: str, *, bold: bool = False) -> str:
    return f"\033[1m{title}\033[0m" if bold else title
