---
type: "AEP evidence"
title: "P1 HOOLA CORE"
generated: { by: "app.aep.audit/0.600.0" }
sources:
  - repo://server/app/aep/messages.py
  - repo://server/app/aep/runnable.py
  - repo://server/app/aep/tools.py
  - repo://server/app/aep/models.py
  - repo://server/app/aep/prompts.py
  - repo://server/app/aep/parsers.py
  - repo://server/app/aep/history.py
  - repo://server/app/aep/stores.py
  - repo://server/app/aep/serializable.py
  - repo://server/tests/test_v0510_hoola_core.py
---

The langchain-core feature surface as house code: messages with the 17 content blocks, the Runnable composition substrate, tools, the chat-model contracts, prompts, parsers, chat history, stores - and the serializable seed P7's loader was reserved for.

Files: `server/app/aep/messages.py` (430 lines), `server/app/aep/runnable.py` (508 lines), `server/app/aep/tools.py` (272 lines), `server/app/aep/models.py` (495 lines), `server/app/aep/prompts.py` (194 lines), `server/app/aep/parsers.py` (97 lines), `server/app/aep/history.py` (61 lines), `server/app/aep/stores.py` (80 lines), `server/app/aep/serializable.py` (64 lines)
Suite: `server/tests/test_v0510_hoola_core.py` (79 tests)

| Upstream feature | Hoola symbol | Proven by |
|---|---|---|
| 17 content block types | `app.aep.messages.CONTENT_BLOCK_TYPES` | `test_seventeen_content_block_types` |
| BaseMessage family (human/ai/system/tool/function/chat) | `app.aep.messages.HumanMessage` | `test_message_family_types` |
| AIMessageChunk '+' merge | `app.aep.messages.AIMessageChunk` | `test_chunk_merge_content_and_id` |
| tool_call_chunk merge by index | `app.aep.messages.ToolCallChunk` | `test_chunk_merge_tool_call_chunks_by_index` |
| message dict round trip | `app.aep.messages.message_to_dict` | `test_message_dict_round_trip` |
| RemoveMessage + REMOVE_ALL_MESSAGES | `app.aep.messages.RemoveMessage` | `test_remove_message_and_sentinel` |
| merge_content shapes | `app.aep.messages.merge_content` | `test_merge_content_shapes` |
| chunk -> message downgrade | `app.aep.messages.message_chunk_to_message` | `test_message_chunk_to_message_downgrade` |
| Runnable invoke/batch/stream | `app.aep.runnable.Runnable` | `test_sequence_pipe_and_invoke` |
| RunnableSequence '|' + ror | `app.aep.runnable.RunnableSequence` | `test_sequence_ror_and_pipe_alias` |
| RunnableParallel (dict literal coercion) | `app.aep.runnable.RunnableParallel` | `test_dict_literal_coerces_to_parallel` |
| batch threaded + ordered | `app.aep.runnable.Runnable` | `test_batch_threaded_and_ordered` |
| batch return_exceptions | `app.aep.runnable.Runnable` | `test_batch_return_exceptions` |
| ainvoke/abatch twins | `app.aep.runnable.Runnable` | `test_ainvoke_and_abatch` |
| RunnableLambda (+ async) | `app.aep.runnable.RunnableLambda` | `test_async_lambda_and_sequence` |
| stream through a sequence | `app.aep.runnable.RunnableSequence` | `test_stream_and_sequence_stream` |
| RunnableBinding kwargs ride config | `app.aep.runnable.RunnableBinding` | `test_binding_kwargs_ride_the_config_channel` |
| with_retry (flaky recovery) | `app.aep.runnable.RunnableRetry` | `test_retry_succeeds_after_flaky_failures` |
| with_fallbacks (second wins / last raise) | `app.aep.runnable.RunnableWithFallbacks` | `test_fallbacks_second_wins` |
| RunnablePassthrough assign | `app.aep.runnable.RunnablePassthrough` | `test_passthrough_and_assign` |
| lambda input schema from hints | `app.aep.runnable.RunnableLambda` | `test_lambda_input_schema_from_basemodel_hint` |
| BaseTool + @tool schema from hints/docstring | `app.aep.tools.tool` | `test_tool_decorator_schema_from_hints_and_docstring` |
| BaseTool subclass contract | `app.aep.tools.BaseTool` | `test_basetool_subclass_contract` |
| tool_call dict -> ToolMessage | `app.aep.tools.BaseTool` | `test_tool_call_dict_returns_tool_message` |
| content_and_artifact | `app.aep.tools.BaseTool` | `test_content_and_artifact_response_format` |
| ToolException + handle_tool_error | `app.aep.tools.ToolException` | `test_tool_exception_and_handle_tool_error` |
| InjectedToolArg hidden from the model schema | `app.aep.tools.InjectedToolArg` | `test_injected_args_hidden_from_model_schema` |
| StructuredTool.from_function | `app.aep.tools.StructuredTool` | `test_structured_tool_from_function` |
| tool as a Runnable (composes) | `app.aep.tools.BaseTool` | `test_tool_is_runnable_and_composes` |
| BaseChatModel _generate/_llm_type contract | `app.aep.models.BaseChatModel` | `test_chat_model_subclass_contract_invoke` |
| message list/dict input coercion | `app.aep.models.BaseChatModel` | `test_chat_model_message_list_and_dict_inputs` |
| generate -> ChatResult | `app.aep.models.BaseChatModel` | `test_generate_returns_chat_result` |
| generate_prompt | `app.aep.models.BaseChatModel` | `test_generate_prompt_uses_prompt_values` |
| InMemoryCache dedupes generate | `app.aep.models.InMemoryCache` | `test_inmemory_cache_dedupes_generate_calls` |
| InMemoryRateLimiter token bucket | `app.aep.models.InMemoryRateLimiter` | `test_rate_limiter_token_bucket` |
| bind_tools honest default refusal | `app.aep.models.BaseChatModel` | `test_bind_tools_default_unsupported` |
| with_structured_output (plain + fenced JSON) | `app.aep.models.BaseChatModel` | `test_with_structured_output_fenced_json_and_system_merge` |
| ModelProfile + UsageMetadata | `app.aep.models.ModelProfile` | `test_model_profile_and_usage_fields_exist` |
| FakeListChatModel stream chunks | `app.aep.models.FakeListChatModel` | `test_fake_stream_chunks` |
| BaseLLM contract | `app.aep.models.BaseLLM` | `test_base_llm_contract` |
| _identifying_params + _llm_string | `app.aep.models.BaseChatModel` | `test_identifying_params_and_llm_string` |
| PromptTemplate (+ partials, missing-var raise) | `app.aep.prompts.PromptTemplate` | `test_prompt_template_from_template_and_format` |
| prompt invoke -> StringPromptValue | `app.aep.prompts.PromptTemplate` | `test_prompt_invoke_returns_string_prompt_value` |
| ChatPromptTemplate from tuples | `app.aep.prompts.ChatPromptTemplate` | `test_chat_prompt_template_from_tuples` |
| MessagesPlaceholder required/optional | `app.aep.prompts.MessagesPlaceholder` | `test_chat_prompt_placeholder_required_and_optional` |
| StrOutputParser | `app.aep.parsers.StrOutputParser` | `test_str_output_parser` |
| JsonOutputParser tolerates fences | `app.aep.parsers.JsonOutputParser` | `test_json_output_parser_tolerates_fences` |
| PydanticOutputParser validates | `app.aep.parsers.PydanticOutputParser` | `test_pydantic_output_parser_validates` |
| parser composes after a model | `app.aep.parsers.BaseOutputParser` | `test_parser_composes_after_model` |
| BaseChatMessageHistory + InMemory | `app.aep.history.InMemoryChatMessageHistory` | `test_inmemory_history_round_trip` |
| get_buffer_string roles | `app.aep.history.get_buffer_string` | `test_buffer_string_roles` |
| BaseStore/InMemoryStore namespaced | `app.aep.stores.InMemoryStore` | `test_inmemory_store_namespaced` |
| store key validation | `app.aep.stores.InvalidKeyException` | `test_store_rejects_bad_keys` |
| InMemoryByteStore bytes only | `app.aep.stores.InMemoryByteStore` | `test_byte_store_bytes_only` |
| Serializable lc shape (the P7 loader seed) | `app.aep.serializable.Serializable` | `test_serializable_lc_shape` |
| lc_id path convention | `app.aep.serializable.Serializable` | `test_serializable_lc_id_path` |

