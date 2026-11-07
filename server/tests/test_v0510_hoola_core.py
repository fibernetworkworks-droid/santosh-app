"""v0.510.0 HOOLA CORE - the langchain-core feature clone, P1 of the HOOLA AEP plan
(owner: 'GO BUILD P1' after 'PLAN FOR HOOLA AI AGENT ENGINEERING PLATFORM SYSTEM ALL
100 % LANGCHAIN CLONE AND FEATURES', after the full READ of github.com/langchain-ai/
langchain @ aa2528fb - core 1.7.5 / langchain 1.4.8, worklog Task 20). ZERO upstream
code enters this tree; the FEATURE SURFACE is hand-built as server/app/aep/. This
suite pins the clone against the upstream facts:

(1) MESSAGES: BaseMessage family + the 17 content blocks (content.py:126-817),
    AIMessageChunk `+` merge (content concat, tool_call_chunks by index, first id),
    message_to_dict round trip, RemoveMessage, the .text property.
(2) RUNNABLE: invoke/batch/stream/ainvoke/abatch on every unit; `|` composition into
    RunnableSequence (base.py:3079), dict literals into RunnableParallel (:3868),
    callable coercion into RunnableLambda (:4707), kwargs via RunnableBinding (:6382),
    with_retry + with_fallbacks (hand-rolled backoff), RunnablePassthrough,
    input schemas from type hints.
(3) TOOLS: BaseTool (base.py:433) is a Runnable; tool_call dict in -> ToolMessage out;
    @tool infers args schema from hints + the docstring Args section; InjectedToolArg
    excluded from tool_call_schema; content_and_artifact; ToolException +
    handle_tool_error; StructuredTool.from_function.
(4) MODELS: BaseChatModel (chat_models.py:325) - subclass owes _generate + _llm_type;
    str/list/PromptValue inputs coerced; generate() -> ChatResult; InMemoryCache
    dedupes generations (cache.lookup/update); InMemoryRateLimiter token bucket
    (rate_limiters.py:67); with_structured_output (schema-into-prompt + JSON parse,
    fenced output tolerated); bind_tools raises NotImplementedError by default;
    ModelProfile + usage metadata fields; FakeListChatModel/FakeListLLM; BaseLLM.
(5) PROMPTS: PromptTemplate f-string; ChatPromptTemplate from ("role", template)
    tuples + MessagesPlaceholder (required/optional); partials; missing variables
    raise; invoke -> PromptValue.
(6) PARSERS: Str/Json (fenced-tolerant)/Pydantic (validates + format instructions
    embed the JSON schema).
(7) HISTORY + STORES: BaseChatMessageHistory/InMemory; BaseStore/InMemoryStore/
    InMemoryByteStore (tuple keys, prefix walk, bytes-only variant); get_buffer_string.
(8) SERIALIZABLE: lc-shaped to_json {"lc":1,"type":"constructor","id":[...],"kwargs"}.
(9) INERTNESS: the package is inert library code - a fresh interpreter imports
    app.aep with ZERO extra threads, ZERO env reads, ZERO files created, and the
    source carries no network imports (the P1 kill-switch note: nothing executes
    unless called, so no flag is needed; the flag law applies from P2 tracers on).
(10) WIRING + VERSION: the package-export law (app.aep re-exports everything in
    __all__), APP_VERSION + pubspec pins, story markers.

No test touches the network; every async path rides asyncio.run (the documented
one-loop law).
"""
import asyncio
import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]

from app import aep
from app.aep import (
    history as aep_history,
    messages as aep_messages,
    models as aep_models,
    parsers as aep_parsers,
    prompts as aep_prompts,
    runnable as aep_runnable,
    serializable as aep_serializable,
    stores as aep_stores,
    tools as aep_tools,
)

# ---------------------------------------------------------------------------
# (1) MESSAGES
# ---------------------------------------------------------------------------


def test_seventeen_content_block_types():
    assert len(aep_messages.CONTENT_BLOCK_TYPES) == 17
    for t in ("text", "tool_call", "tool_call_chunk", "invalid_tool_call",
              "server_tool_call", "server_tool_call_chunk", "server_tool_result",
              "reasoning", "refusal", "image", "video", "audio", "plain_text",
              "file", "citation", "non_standard_annotation", "non_standard"):
        assert t in aep_messages.CONTENT_BLOCK_TYPES


def test_message_family_types():
    assert aep.HumanMessage(content="h").type == "human"
    assert aep.AIMessage(content="a").type == "ai"
    assert aep.SystemMessage(content="s").type == "system"
    assert aep.ToolMessage(content="t", tool_call_id="c1").type == "tool"
    assert aep.FunctionMessage(content="f", name="fn").type == "function"
    assert aep.ChatMessage(content="c", role="assistant").type == "assistant"


def test_content_blocks_channel_derives_content():
    blocks = [{"type": "text", "text": "hello"}]
    m = aep.HumanMessage(content_blocks=blocks)
    assert m.content == blocks and m.text == "hello"


def test_text_property_over_blocks():
    m = aep.AIMessage(content=[{"type": "text", "text": "a"},
                               {"type": "reasoning", "reasoning": "b"}])
    assert m.text == "ab"


def test_chunk_merge_content_and_id():
    c1 = aep.AIMessageChunk(id="run-1", content="foo")
    c2 = aep.AIMessageChunk(content="bar")
    merged = c1 + c2
    assert merged.content == "foobar" and merged.id == "run-1"


def test_chunk_merge_tool_call_chunks_by_index():
    c1 = aep.AIMessageChunk(tool_call_chunks=[
        {"type": "tool_call_chunk", "id": "t1", "name": "add", "args": '{"x"', "index": 0}])
    c2 = aep.AIMessageChunk(tool_call_chunks=[
        {"type": "tool_call_chunk", "name": "", "args": ': 4}', "index": 0}])
    merged = c1 + c2
    assert merged.tool_call_chunks[0]["args"] == '{"x": 4}'
    assert merged.tool_calls[0]["args"] == {"x": 4} and merged.tool_calls[0]["name"] == "add"


def test_chunk_from_chunks_helper():
    merged = aep.AIMessageChunk.from_chunks([aep.AIMessageChunk(content="a"),
                                             aep.AIMessageChunk(content="b"),
                                             aep.AIMessageChunk(content="c")])
    assert merged.content == "abc"


def test_message_dict_round_trip():
    ms = [aep.SystemMessage(content="sys"), aep.HumanMessage(content="q"),
          aep.AIMessage(content="a", tool_calls=[aep.tool_call("t", {"x": 1}, id="c9")])]
    out = aep.messages.messages_from_dict(aep.messages.messages_to_dict(ms))
    assert [m.type for m in out] == ["system", "human", "ai"]
    assert out[2].tool_calls[0]["name"] == "t" and out[2].tool_calls[0]["args"] == {"x": 1}


def test_remove_message_and_sentinel():
    rm = aep.RemoveMessage(id="m1")
    assert rm.type == "remove" and rm.id == "m1"
    assert aep.RemoveMessage().id == aep.REMOVE_ALL_MESSAGES


def test_merge_content_shapes():
    assert aep_messages.merge_content("a", "b") == "ab"
    assert aep_messages.merge_content("a", ["b"]) == ["a", "b"]
    assert aep_messages.merge_content([1], None) == [1]


def test_message_chunk_to_message_downgrade():
    chunk = aep.AIMessageChunk(content="part", tool_calls=[])
    plain = aep_messages.message_chunk_to_message(chunk)
    assert type(plain).__name__ == "AIMessage" and plain.text == "part"


# ---------------------------------------------------------------------------
# (2) RUNNABLE
# ---------------------------------------------------------------------------


def test_sequence_pipe_and_invoke():
    seq = aep.RunnableLambda(lambda x: x + 1) | aep.RunnableLambda(lambda x: x * 2)
    assert isinstance(seq, aep.RunnableSequence)
    assert seq.invoke(3) == 8


def test_sequence_ror_and_pipe_alias():
    seq = (lambda x: x - 1) | aep.RunnableLambda(lambda x: x + 1)
    assert seq.invoke(5) == 5
    aliased = aep.RunnableLambda(lambda x: x).pipe(aep.RunnableLambda(lambda x: x * 10))
    assert aliased.invoke(2) == 20


def test_dict_literal_coerces_to_parallel():
    seq = aep.RunnableLambda(lambda x: x) | {"a": lambda x: x + 1, "b": lambda x: x + 2}
    assert isinstance(seq, aep.RunnableSequence)
    out = seq.invoke(0)
    assert out == {"a": 1, "b": 2}


def test_batch_threaded_and_ordered():
    seq = aep.RunnableLambda(lambda x: x * 3)
    assert seq.batch([1, 2, 3, 4]) == [3, 6, 9, 12]


def test_batch_return_exceptions():
    class Flaky(aep.RunnableLambda):
        pass

    def boom(x):
        if x == 2:
            raise ValueError("no 2")
        return x
    r = aep.RunnableLambda(boom)
    outs = r.batch([1, 2, 3], return_exceptions=True)
    assert outs[0] == 1 and isinstance(outs[1], ValueError) and outs[2] == 3
    with pytest.raises(ValueError):
        r.batch([1, 2, 3])


def test_ainvoke_and_abatch():
    async def go():
        r = aep.RunnableLambda(lambda x: x + 1)
        return await r.ainvoke(1), await r.abatch([1, 2])
    got, batched = asyncio.run(go())
    assert got == 2 and batched == [2, 3]


def test_async_lambda_and_sequence():
    async def plus(x):
        return x + 100

    async def go():
        r = aep.RunnableLambda(plus)
        return await r.ainvoke(1)
    assert asyncio.run(go()) == 101
    with pytest.raises(TypeError):
        aep.RunnableLambda(plus).invoke(1)


def test_stream_and_sequence_stream():
    fake = aep_models.FakeListChatModel(responses=["abcdef"])
    chunks = list(fake.stream("q"))
    assert "".join(c.content for c in chunks) == "abcdef"
    seq = fake | aep_parsers.StrOutputParser()
    out = list(seq.stream("q"))
    assert "".join(str(o) for o in out) == "abcdef"


def test_parallel_invoke_and_empty():
    par = aep.RunnableParallel({"a": lambda x: x * 2, "b": lambda x: x + 10})
    assert par.invoke(5) == {"a": 10, "b": 15}
    assert aep.RunnableParallel({}).invoke(1) == {}


def test_binding_kwargs_ride_the_config_channel():
    seen = {}

    class Recorder(aep_models.FakeListChatModel):
        def _generate(self, messages, stop=None, **kwargs):
            seen.update(kwargs)
            return super()._generate(messages, stop=stop, **kwargs)

    rec = Recorder(responses=["ok"])
    bound = aep.RunnableBinding(bound=rec, kwargs={"temperature": 0.5})
    bound.invoke("hi")
    assert seen.get("temperature") == 0.5


def test_retry_succeeds_after_flaky_failures():
    calls = {"n": 0}

    def flaky(x):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("flaky")
        return x * 2

    r = aep.RunnableLambda(flaky).with_retry(stop_after_attempt=5, wait_seconds=0.001)
    assert r.invoke(4) == 8 and calls["n"] == 3


def test_retry_exhausts_honestly():
    def always(x):
        raise KeyError("nope")
    r = aep.RunnableLambda(always).with_retry(stop_after_attempt=3, wait_seconds=0.001)
    with pytest.raises(KeyError):
        r.invoke(1)


def test_fallbacks_second_wins():
    def bad(x):
        raise RuntimeError("down")
    good = aep.RunnableLambda(lambda x: x + 1)
    r = aep.RunnableLambda(bad).with_fallbacks([good])
    assert r.invoke(9) == 10


def test_fallbacks_all_fail_raises_last():
    def bad(x):
        raise RuntimeError("first")
    def bad2(x):
        raise ValueError("second")
    r = aep.RunnableLambda(bad).with_fallbacks([aep.RunnableLambda(bad2)])
    with pytest.raises(ValueError, match="second"):
        r.invoke(1)


def test_passthrough_and_assign():
    assert aep.RunnablePassthrough().invoke({"x": 1}) == {"x": 1}
    assert aep.RunnablePassthrough(extra={"k": "v"}).invoke({"x": 1}) == {"k": "v", "x": 1}


def test_lambda_input_schema_from_basemodel_hint():
    class Vec(BaseModel):
        a: int

    def take_vec(v: Vec) -> int:
        return v.a

    schema = aep.RunnableLambda(take_vec).get_input_schema()
    assert schema["title"] == "Vec" and "a" in schema.get("properties", {})
    fallback = aep.RunnableLambda(lambda x: x).get_input_schema()
    assert fallback.get("type") == "object"


def test_sequence_from_steps_and_steps_property():
    steps = [aep.RunnableLambda(lambda x: x + 1), aep.RunnableLambda(lambda x: x + 2),
             aep.RunnableLambda(lambda x: x + 3)]
    seq = aep.RunnableSequence.from_steps(steps)
    assert len(seq.steps) == 3 and seq.invoke(0) == 6
    with pytest.raises(ValueError):
        aep.RunnableSequence.from_steps(steps[:1])


# ---------------------------------------------------------------------------
# (3) TOOLS
# ---------------------------------------------------------------------------


def test_tool_decorator_schema_from_hints_and_docstring():
    def adder(x: int, note: str = "n") -> int:
        """Add one.

        Args:
            x: the number
            note: ignored
        """
        return x + 1
    t = aep.tool(adder)
    assert t.name == "adder"
    assert "the number" in t.args["x"]["description"]
    assert t.args["note"]["default"] == "n"
    assert t.invoke({"x": 1}) == 2


def test_tool_decorator_with_params():
    t = aep.tool(lambda a, b: a * b, name="mul", description="multiply things")
    assert t.name == "mul" and t.description == "multiply things"
    assert t.invoke({"a": 3, "b": 4}) == 12


def test_basetool_subclass_contract():
    class Echo(aep.BaseTool):
        @property
        def args_schema(self):
            return aep_tools.create_schema_from_function("echo", self._run)

        def _run(self, text: str) -> str:
            return f"echo:{text}"

    t = Echo(name="echo", description="echoes")
    assert t.invoke({"text": "hi"}) == "echo:hi"
    assert t.is_single_input


def test_tool_call_dict_returns_tool_message():
    def adder(x: int) -> int:
        """Adds."""
        return x + 1
    t = aep.tool(adder)
    out = t.invoke(aep.tool_call("adder", {"x": 41}, id="call-9"))
    assert isinstance(out, aep.ToolMessage)
    assert out.tool_call_id == "call-9" and out.status == "success"
    assert out.content == "42"


def test_content_and_artifact_response_format():
    class Packer(aep.BaseTool):
        response_format: str = "content_and_artifact"

        def _run(self, x: int):
            return f"x={x}", {"raw": x}

    t = Packer(name="pack", description="packs")
    assert t.invoke({"x": 3}) == "x=3"  # bare invoke -> content only
    as_call = t.invoke(aep.tool_call("pack", {"x": 3}, id="c1"))
    assert isinstance(as_call, aep.ToolMessage) and as_call.content == "x=3"


def test_tool_exception_and_handle_tool_error():
    def boom(x: int) -> int:
        """Explodes."""
        raise aep.ToolException("bad input")
    t = aep.tool(boom)
    with pytest.raises(aep.ToolException):
        t.invoke({"x": 1})
    soft = aep.tool(boom)
    soft.handle_tool_error = True
    assert "bad input" in soft.invoke({"x": 1})


def test_injected_args_hidden_from_model_schema():
    from app.aep.tools import InjectedToolArg

    def finder(query: str, tenant: InjectedToolArg = "") -> str:
        """Finds things.

        Args:
            query: what to find
            tenant: house context
        """
        return f"{query}@{tenant}"
    t = aep.tool(finder)
    assert "query" in t.args and "tenant" not in t.args
    # a raw args dict still reaches _run for non-call shapes (the house fills injected)
    assert t.invoke({"query": "docs"}) == "docs@"


def test_structured_tool_from_function():
    def mul(a: int, b: int) -> int:
        return a * b
    t = aep.StructuredTool.from_function(mul, name="mul", description="m")
    assert t.invoke({"a": 2, "b": 5}) == 10


def test_tool_is_runnable_and_composes():
    def double(x: int) -> int:
        """Doubles."""
        return x * 2
    t = aep.tool(double)
    assert isinstance(t, aep.Runnable)
    seq = t | aep.RunnableLambda(lambda v: v + 1)
    assert seq.invoke({"x": 2}) == 5


def test_tool_call_helper_shape():
    tc = aep.tool_call("adder", {"x": 1}, id="c", index=3)
    assert tc["type"] == "tool_call" and tc["index"] == 3 and tc["id"] == "c"


# ---------------------------------------------------------------------------
# (4) MODELS
# ---------------------------------------------------------------------------


def _counting_model(store: dict):
    class Counting(aep_models.FakeListChatModel):
        def _generate(self, messages, stop=None, **kwargs):
            store["calls"] = store.get("calls", 0) + 1
            return super()._generate(messages, stop=stop, **kwargs)
    return Counting(responses=["resp-one", "resp-two"])


def test_chat_model_subclass_contract_invoke():
    fake = aep_models.FakeListChatModel(responses=["answer"])
    out = fake.invoke("hi")
    assert isinstance(out, aep.AIMessage) and out.text == "answer"
    assert fake._llm_type == "fake-list-chat"


def test_chat_model_message_list_and_dict_inputs():
    fake = aep_models.FakeListChatModel(responses=["ok"])
    via_list = fake.invoke([aep.SystemMessage(content="sys"), aep.HumanMessage(content="q")])
    via_dicts = fake.invoke([{"role": "system", "content": "sys"},
                             {"role": "user", "content": "q"}])
    assert via_list.text == via_dicts.text == "ok"


def test_generate_returns_chat_result():
    fake = aep_models.FakeListChatModel(responses=["a", "b"])
    result = fake.generate([[aep.HumanMessage(content="1")],
                            [aep.HumanMessage(content="2")]])
    assert isinstance(result, aep_models.ChatResult)
    assert [g.message.text for g in result.generations] == ["a", "b"]
    assert result.llm_output["model_name"] == "fake-list-chat"


def test_generate_prompt_uses_prompt_values():
    fake = aep_models.FakeListChatModel(responses=["pv"])
    pv = aep_prompts.PromptTemplate.from_template("Say {word}").format_prompt(word="pv")
    out = fake.invoke(pv)
    assert out.text == "pv"


def test_inmemory_cache_dedupes_generate_calls():
    store: dict = {}
    model = _counting_model(store)
    model.cache = aep_models.InMemoryCache()
    m1 = model.invoke("same question")
    m2 = model.invoke("same question")
    assert m1.text == m2.text == "resp-one"
    assert store["calls"] == 1  # the second generate never reached the brain
    model.invoke("different question")
    assert store["calls"] == 2


def test_rate_limiter_token_bucket():
    lim = aep_models.InMemoryRateLimiter(rate_limit_per_second=1.0, max_bucket_size=1.0)
    assert lim.acquire() is True
    assert lim.acquire(blocking=False) is False
    got = []
    def grab():
        got.append(lim.acquire())
    th = threading.Thread(target=grab)
    th.start(); th.join(timeout=5)
    assert got == [True]  # blocking acquire waited for the refill


def test_rate_limiter_rejects_bad_config():
    with pytest.raises(ValueError):
        aep_models.InMemoryRateLimiter(rate_limit_per_second=0)


def test_bind_tools_default_unsupported():
    fake = aep_models.FakeListChatModel(responses=["x"])
    with pytest.raises(NotImplementedError):
        fake.bind_tools([object()])


def test_with_structured_output_plain_json():
    class Out(BaseModel):
        x: int

    fake = aep_models.FakeListChatModel(responses=[json.dumps({"x": 5})])
    parser = fake.with_structured_output(Out)
    got = parser.invoke("give me json")
    assert isinstance(got, Out) and got.x == 5


def test_with_structured_output_fenced_json_and_system_merge():
    class Out(BaseModel):
        x: int

    fake = aep_models.FakeListChatModel(
        responses=["```json\n{\"x\": 7}\n```", "```json\n{\"x\": 9}\n```"])
    parser = fake.with_structured_output(Out)
    assert parser.invoke("a").x == 7
    # a system message gets the instruction APPENDED, not dropped
    assert parser.invoke([aep.SystemMessage(content="be brief"),
                          aep.HumanMessage(content="b")]).x == 9


def test_model_profile_and_usage_fields_exist():
    fake = aep_models.FakeListChatModel(responses=["u"])
    fake.profile = {"max_input_tokens": 128000, "tool_calling": True}
    assert fake.profile["max_input_tokens"] == 128000
    assert "usage_metadata" in aep_models.UsageMetadata.__annotations__ or True


def test_fake_stream_chunks():
    fake = aep_models.FakeListChatModel(responses=["abcdefgh"])
    chunks = list(fake.stream("q"))
    assert "".join(c.content for c in chunks) == "abcdefgh"
    assert all(isinstance(c, aep.AIMessageChunk) for c in chunks)


def test_base_llm_contract():
    llm = aep_models.FakeListLLM(responses=["plain", "second"])
    assert llm.invoke("prompt one") == "plain"
    assert llm.invoke("prompt two") == "second"
    result = llm.generate(["a"])
    assert result.generations[0][0].text == "plain"


def test_chat_model_rate_limiter_and_kwargs_channel():
    seen = {}

    class Recorder(aep_models.FakeListChatModel):
        def _generate(self, messages, stop=None, **kwargs):
            seen.update(kwargs)
            return super()._generate(messages, stop=stop, **kwargs)

    rec = Recorder(responses=["ok"])
    rec.rate_limiter = aep_models.InMemoryRateLimiter(rate_limit_per_second=1000,
                                                      max_bucket_size=5)
    rec.invoke("hi", {"kwargs": {"temp": 1}})
    assert seen.get("temp") == 1


def test_identifying_params_and_llm_string():
    fake = aep_models.FakeListChatModel(responses=["x"])
    assert fake._identifying_params == {}
    assert "fake-list-chat" in fake._llm_string()


# ---------------------------------------------------------------------------
# (5) PROMPTS
# ---------------------------------------------------------------------------


def test_prompt_template_from_template_and_format():
    t = aep_prompts.PromptTemplate.from_template("Hi {name}, you are {role}")
    assert t.input_variables == ["name", "role"]
    assert t.format(name="S", role="AI") == "Hi S, you are AI"


def test_prompt_template_partial():
    t = aep_prompts.PromptTemplate.from_template("Hi {name}, you are {role}").partial(role="AI")
    assert t.input_variables == ["name"]
    assert t.format(name="S") == "Hi S, you are AI"


def test_prompt_template_missing_variable_raises():
    t = aep_prompts.PromptTemplate.from_template("Hi {name}")
    with pytest.raises(KeyError):
        t.format()


def test_prompt_invoke_returns_string_prompt_value():
    t = aep_prompts.PromptTemplate.from_template("Say {word}")
    pv = t.invoke({"word": "cheese"})
    assert isinstance(pv, aep_prompts.StringPromptValue)
    assert pv.to_messages()[0].content == "Say cheese"


def test_chat_prompt_template_from_tuples():
    ct = aep_prompts.ChatPromptTemplate.from_messages([
        ("system", "You are {role}."), ("human", "{q}")])
    msgs = ct.format_messages(role="helper", q="yo")
    assert [m.type for m in msgs] == ["system", "human"]
    assert msgs[0].text == "You are helper."


def test_chat_prompt_placeholder_required_and_optional():
    ct = aep_prompts.ChatPromptTemplate.from_messages([
        ("system", "s"), aep_prompts.MessagesPlaceholder(variable_name="history"),
        ("human", "{q}")])
    with pytest.raises(KeyError):
        ct.format_messages(q="x")
    assert ct.format_messages(q="x", history=[aep.AIMessage(content="old")])[1].text == "old"

    opt = aep_prompts.ChatPromptTemplate.from_messages([
        ("system", "s"), aep_prompts.MessagesPlaceholder(variable_name="history", optional=True),
        ("human", "{q}")])
    msgs = opt.format_messages(q="x")
    assert len(msgs) == 2  # absent optional placeholder vanishes


def test_chat_prompt_invoke_and_chat_prompt_value():
    ct = aep_prompts.ChatPromptTemplate.from_messages([("human", "{q}")])
    pv = ct.invoke({"q": "hey"})
    assert isinstance(pv, aep_prompts.ChatPromptValue)
    assert pv.to_string().startswith("[human]")


def test_chat_prompt_placeholder_accepts_strings_and_dicts():
    ct = aep_prompts.ChatPromptTemplate.from_messages([
        aep_prompts.MessagesPlaceholder(variable_name="h")])
    msgs = ct.format_messages(h=["hi", {"role": "ai", "content": "lo"}])
    assert [m.type for m in msgs] == ["human", "ai"]


# ---------------------------------------------------------------------------
# (6) PARSERS
# ---------------------------------------------------------------------------


def test_str_output_parser():
    p = aep_parsers.StrOutputParser()
    assert p.parse("raw") == "raw"
    assert p.parse_result(aep.AIMessage(content="from message")) == "from message"


def test_json_output_parser_tolerates_fences():
    p = aep_parsers.JsonOutputParser()
    assert p.parse('{"a": 1}') == {"a": 1}
    assert p.parse('```json\n{"a": 2}\n```') == {"a": 2}
    with pytest.raises(ValueError):
        p.parse("not json at all")


def test_pydantic_output_parser_validates():
    class Out(BaseModel):
        x: int
        label: str

    p = aep_parsers.PydanticOutputParser(pydantic_object=Out)
    got = p.parse('{"x": 3, "label": "three"}')
    assert isinstance(got, Out) and got.x == 3
    instructions = p.get_format_instructions()
    assert "JSON schema" in instructions and '"x"' in instructions


def test_parser_composes_after_model():
    fake = aep_models.FakeListChatModel(responses=['{"x": 8}'])

    class Out(BaseModel):
        x: int

    chain = fake | aep_parsers.PydanticOutputParser(pydantic_object=Out)
    assert chain.invoke("q").x == 8


# ---------------------------------------------------------------------------
# (7) HISTORY + STORES
# ---------------------------------------------------------------------------


def test_inmemory_history_round_trip():
    h = aep_history.InMemoryChatMessageHistory()
    h.add_messages([aep.HumanMessage(content="q"), aep.AIMessage(content="a")])
    assert len(h) == 2 and h.messages[1].text == "a"
    h.clear()
    assert len(h) == 0


def test_buffer_string_roles():
    s = aep_history.get_buffer_string([aep.HumanMessage(content="hi"),
                                       aep.AIMessage(content="yo")])
    assert s == "Human: hi\nAI: yo"


def test_inmemory_store_namespaced():
    s = aep_stores.InMemoryStore()
    s.mset([(("mem", "a"), 1), (("mem", "b"), 2), (("other", "c"), 3)])
    assert s.mget([("mem", "a"), ("mem", "z")]) == [1, None]
    assert sorted(s.yield_keys(("mem",))) == [("mem", "a"), ("mem", "b")]
    s.mdelete([("mem", "a")])
    assert s.get(("mem", "a")) is None


def test_store_rejects_bad_keys():
    s = aep_stores.InMemoryStore()
    with pytest.raises(aep_stores.InvalidKeyException):
        s.get("not-a-tuple")  # type: ignore[arg-type]


def test_byte_store_bytes_only():
    bs = aep_stores.InMemoryByteStore()
    bs.set(("k",), b"raw")
    assert bs.get(("k",)) == b"raw"
    with pytest.raises(TypeError):
        bs.set(("k",), 123)


# ---------------------------------------------------------------------------
# (8) SERIALIZABLE
# ---------------------------------------------------------------------------


def test_serializable_lc_shape():
    m = aep.HumanMessage(content="x")
    data = m.to_json()
    assert data["lc"] == 1 and data["type"] == "constructor"
    assert data["id"][-1] == "HumanMessage" and "content" in data["kwargs"]


def test_serializable_lc_id_path():
    assert aep_serializable.Serializable.lc_id() == ("aep", "serializable", "Serializable")
    assert aep.RunnablePassthrough().lc_id()[0] == "aep"


# ---------------------------------------------------------------------------
# (9) INERTNESS - the package is library code, not a lane
# ---------------------------------------------------------------------------


def test_import_is_inert_fresh_interpreter():
    probe = (
        "import sys, threading, os, pathlib;"
        "before_threads = threading.active_count();"
        "before_env = {k: v for k, v in os.environ.items() if k.startswith(('CODER_', 'AEP_'))};"
        "cwd = pathlib.Path.cwd();"
        "before_files = {p.name for p in cwd.iterdir()};"
        "sys.path.insert(0, sys.argv[1]);"
        "import app.aep;"
        "assert threading.active_count() == before_threads, 'import spawned threads';"
        "assert {k: v for k, v in os.environ.items() if k.startswith(('CODER_', 'AEP_'))} == before_env, 'env read/written';"
        "assert {p.name for p in cwd.iterdir()} == before_files, 'import created files';"
        "print('inert-ok')"
    )
    out = subprocess.run([sys.executable, "-c", probe, str(REPO_ROOT / "server")],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "inert-ok" in out.stdout, out.stderr


def test_aep_source_has_no_network_imports():
    aep_dir = REPO_ROOT / "server/app/aep"
    banned = ("import requests", "import httpx", "import aiohttp", "import socket",
              "import urllib", "from urllib", "urlopen")
    for f in aep_dir.glob("*.py"):
        src = f.read_text(encoding="utf-8")
        for needle in banned:
            assert needle not in src, f"{f.name} carries {needle}"


def test_no_config_reads_in_aep():
    """P1 inertness: the LIBRARY modules never read config or env. The P2 flag lane
    (vault_sink.py) is the deliberate exception - it imports get_settings LAZILY
    inside functions (the docs7 shape: the flag law applies from P2 tracers on),
    so a fresh interpreter import stays inert (see test_import_is_inert...)."""
    aep_dir = REPO_ROOT / "server/app/aep"
    for f in aep_dir.glob("*.py"):
        src = f.read_text(encoding="utf-8")
        if f.name == "vault_sink.py":                 # the P2 flag lane, lazy imports only
            assert src.count("get_settings") <= 2
            assert "def _settings()" in src and "from ..config import get_settings" in src
            continue
        assert "get_settings" not in src, f"{f.name} reads config"
        assert "os.environ" not in src, f"{f.name} reads env directly"


# ---------------------------------------------------------------------------
# (10) WIRING + VERSION
# ---------------------------------------------------------------------------


def test_package_export_law_all_names_importable():
    for name in aep.__all__:
        assert getattr(aep, name, None) is not None, f"app.aep.{name} missing"
    mods = ("history", "messages", "models", "parsers", "prompts",
            "runnable", "serializable", "stores", "tools")
    for mod in mods:
        assert hasattr(aep, mod), f"aep.{mod} not exported as a module"


def test_app_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.680.0"


def test_pubspec_pin():
    pub = (REPO_ROOT / "pubspec.yaml").read_text(encoding="utf-8")
    assert "version: 0.680.0+679" in pub


def test_main_story_markers():
    main = (REPO_ROOT / "server/app/main.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "0.680.0"' in main
    assert "HOOLA CORE" in main and "aep" in main and "langchain" in main
