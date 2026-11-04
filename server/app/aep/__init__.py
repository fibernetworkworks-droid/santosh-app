"""HOOLA AEP - the Hoola Agent Engineering Platform substrate (v0.510.0 HOOLA CORE,
P1 of the AEP plan). The langchain-core FEATURE SURFACE cloned into house code after
the end-to-end read of github.com/langchain-ai/langchain @ aa2528fb (core 1.7.5 /
langchain 1.4.8, Task 20 of the worklog) - ZERO upstream code or imports (the port
law that built coder/skills/nudge/delegate/curator/docs7).

What lives here (every module inert until called - no network, no threads on import,
no config reads, no kill switch needed because nothing executes; the flag law applies
from P2 where tracers and agents actually run):

- messages   : BaseMessage + the 17 content blocks + AIMessageChunk merge + dict round trip
- runnable   : Runnable ABC (invoke/batch/stream + `|`), Sequence/Parallel/Lambda/
               Binding/Passthrough, with_retry, with_fallbacks
- tools      : BaseTool, StructuredTool, @tool (schema from hints + docstring),
               InjectedToolArg, tool_call helper
- models     : BaseChatModel + BaseLLM contracts, InMemoryCache, InMemoryRateLimiter,
               ModelProfile, FakeListChatModel/FakeListLLM
- prompts    : PromptTemplate, ChatPromptTemplate, MessagesPlaceholder, partials
- parsers    : Str/Json/Pydantic output parsers
- history    : BaseChatMessageHistory + InMemoryChatMessageHistory
- stores     : BaseStore + InMemoryStore + InMemoryByteStore
- serializable: the lc-shaped to_json seed (P7 HUB builds the loader on it)

P2 (HOOLA TRACE) adds tracers/run trees; P3 (HOOLA GRAPH) the state-graph engine;
P4 (HOOLA AGENT) create_agent; P5 the 24-middleware framework; P6 retrieval;
P7 the hub/loader/conformance suite.
"""
from . import (  # noqa: F401 - the package-export law (the v0.478 lesson, extended)
    history,
    messages,
    models,
    parsers,
    prompts,
    parsers as _parsers_mod,
    runnable,
    serializable,
    stores,
    tools,
)
from .history import BaseChatMessageHistory, InMemoryChatMessageHistory, get_buffer_string
from .messages import (
    CONTENT_BLOCK_TYPES,
    REMOVE_ALL_MESSAGES,
    AIMessage,
    AIMessageChunk,
    AudioContentBlock,
    BaseMessage,
    ChatMessage,
    Citation,
    FileContentBlock,
    FunctionMessage,
    HumanMessage,
    ImageContentBlock,
    InvalidToolCall,
    NonStandardAnnotation,
    NonStandardContentBlock,
    PlainTextContentBlock,
    ReasoningContentBlock,
    RefusalContentBlock,
    RemoveMessage,
    ServerToolCall,
    ServerToolCallChunk,
    ServerToolResult,
    SystemMessage,
    TextContentBlock,
    ToolCall,
    ToolCallChunk,
    ToolMessage,
    VideoContentBlock,
    message_to_dict,
    messages_from_dict,
    messages_to_dict,
    merge_content,
    message_chunk_to_message,
)
from .models import (
    BaseCache,
    BaseChatModel,
    BaseLLM,
    BaseRateLimiter,
    ChatGeneration,
    ChatResult,
    FakeListChatModel,
    FakeListLLM,
    Generation,
    InMemoryCache,
    InMemoryRateLimiter,
    LLMResult,
    ModelProfile,
    UsageMetadata,
)
from .parsers import BaseOutputParser, JsonOutputParser, PydanticOutputParser, StrOutputParser
from .prompts import (
    BasePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from .runnable import (
    Runnable,
    RunnableBinding,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
    RunnableRetry,
    RunnableSequence,
    RunnableWithFallbacks,
)
from .serializable import Serializable
from .stores import BaseStore, InMemoryByteStore, InMemoryStore, InvalidKeyException
from .tools import BaseTool, InjectedToolArg, StructuredTool, ToolException, tool, tool_call

__all__ = [
    "CONTENT_BLOCK_TYPES", "REMOVE_ALL_MESSAGES",
    # messages
    "BaseMessage", "HumanMessage", "AIMessage", "AIMessageChunk", "SystemMessage",
    "ChatMessage", "ToolMessage", "FunctionMessage", "RemoveMessage",
    "ToolCall", "ToolCallChunk", "InvalidToolCall",
    "ServerToolCall", "ServerToolCallChunk", "ServerToolResult",
    "ReasoningContentBlock", "RefusalContentBlock",
    "ImageContentBlock", "VideoContentBlock", "AudioContentBlock",
    "PlainTextContentBlock", "FileContentBlock",
    "Citation", "NonStandardAnnotation", "NonStandardContentBlock",
    "TextContentBlock",
    "merge_content", "message_chunk_to_message", "message_to_dict",
    "messages_to_dict", "messages_from_dict",
    # runnable
    "Runnable", "RunnableSequence", "RunnableParallel", "RunnableLambda",
    "RunnablePassthrough", "RunnableBinding", "RunnableRetry",
    "RunnableWithFallbacks",
    # tools
    "BaseTool", "StructuredTool", "tool", "tool_call", "ToolException",
    "InjectedToolArg",
    # models
    "BaseChatModel", "BaseLLM", "BaseCache", "InMemoryCache",
    "BaseRateLimiter", "InMemoryRateLimiter", "ModelProfile", "UsageMetadata",
    "ChatGeneration", "ChatResult", "Generation", "LLMResult",
    "FakeListChatModel", "FakeListLLM",
    # prompts + parsers
    "PromptTemplate", "ChatPromptTemplate", "MessagesPlaceholder",
    "BasePromptTemplate",
    "BaseOutputParser", "StrOutputParser", "JsonOutputParser", "PydanticOutputParser",
    # history + stores + serializable
    "BaseChatMessageHistory", "InMemoryChatMessageHistory", "get_buffer_string",
    "BaseStore", "InMemoryStore", "InMemoryByteStore", "InvalidKeyException",
    "Serializable",
]
