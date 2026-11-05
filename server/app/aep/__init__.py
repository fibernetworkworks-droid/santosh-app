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
- tracers    : (P2 v0.521.0 HOOLA TRACE) CallbackManager + handlers, Run/run tree,
               RunTreeTracer, InMemoryRunStore, astream_events v2, the Span fire seam
- vault_sink : (P2) the flag-gated run persistence - runs land as vault observations
               typed 'aep_run', redacted before storage (aep_trace, default OFF)
- graph      : (P3 v0.530.0 HOOLA GRAPH) the state-graph engine - StateGraph
               (nodes/edges/conditional, fan-out + join barriers), add_messages +
               AgentState, interrupt/Command park-and-resume, MemorySaver +
               SqliteSaver checkpointers, store wiring
- agent      : (P4 v0.549.0 HOOLA AGENT) create_agent - the agent loop compiled
               onto the house graph (model node + ToolNode + pending-tool_calls
               routing + return_direct + response_format -> structured_response
               + interrupt_before/after breakpoints + checkpointer chat memory)
- middleware : (P5 v0.559.0 HOOLA MIDDLEWARE) the 24 - the hook taxonomy
               (before_agent/before_model/wrap_model_call/after_model/
               after_agent/wrap_tool_call + ModelRequest.override + jump_to as
               an ephemeral untracked channel) and the middlewares in tiers
               (summarization, PII + the live stream transformer, model+tool
               call limits, retry+fallback, tool error/retry/emulator,
               human-in-the-loop on the P3 park seam, todo, context editing,
               file search, provider tool search, the bounded shell tool) +
               THE UNIFICATION: nudge/curator/delegate/skills-primer collapse
               into middlewares on the one loop

P3 (HOOLA GRAPH) is the state-graph engine; P4 (HOOLA AGENT) create_agent; P5 (HOOLA MIDDLEWARE) the 24;
P6 retrieval; P7 the hub/loader/conformance suite.
"""
from . import (  # noqa: F401 - the package-export law (the v0.478 lesson, extended)
    agent,
    history,
    messages,
    middleware,
    models,
    parsers,
    prompts,
    parsers as _parsers_mod,
    graph,
    runnable,
    serializable,
    stores,
    tools,
    tracers,
    vault_sink,
)
from .agent import ToolNode, create_agent, create_react_agent
from .graph import (
    INTERRUPT_KEY,
    END,
    START,
    AgentState,
    BaseCheckpointSaver,
    Command,
    CompiledStateGraph,
    GraphInterrupt,
    GraphRecursionError,
    MemorySaver,
    SqliteSaver,
    StateGraph,
    add_messages,
    interrupt,
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
from .tracers import (
    RUN_TYPES,
    BaseCallbackHandler,
    CallbackManager,
    InMemoryRunStore,
    Run,
    RunSink,
    RunTreeTracer,
    Span,
    astream_events,
    callbacks_from_config,
    dumps_safe,
    global_tracer,
    reset_global,
    traced_invoke,
)
from .vault_sink import STATS as TRACE_STATS
from .vault_sink import VaultRunSink, attach_vault_sink, trace_enabled, vault_run_by_id, vault_runs

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
    # P2 tracers (HOOLA TRACE)
    "RUN_TYPES", "BaseCallbackHandler", "CallbackManager", "Span", "Run",
    "RunSink", "RunTreeTracer", "InMemoryRunStore", "astream_events",
    "callbacks_from_config", "dumps_safe", "global_tracer", "reset_global",
    "traced_invoke", "VaultRunSink", "attach_vault_sink", "trace_enabled",
    "vault_runs", "vault_run_by_id", "TRACE_STATS",
    # P3 graph (HOOLA GRAPH)
    "START", "END", "INTERRUPT_KEY", "AgentState", "add_messages",
    "BaseCheckpointSaver", "MemorySaver", "SqliteSaver",
    "Command", "CompiledStateGraph", "GraphInterrupt", "GraphRecursionError",
    "StateGraph", "interrupt",
    # P4 agent (HOOLA AGENT)
    "ToolNode", "create_agent", "create_react_agent",
]
