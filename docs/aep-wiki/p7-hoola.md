---
type: "AEP evidence"
title: "P7 HOOLA HUB"
generated: { by: "app.aep.audit/0.600.0" }
sources:
  - repo://server/app/aep/hub.py
  - repo://server/app/aep/load.py
  - repo://server/app/aep/mcp.py
  - repo://server/app/aep/conformance.py
  - repo://server/tests/test_v0570_hoola_hub.py
---

The hub: init_chat_model over Hoola's brains (fake / hoola-injected-runner / the openai_compat BYOK zoo), the ConfigurableModel declarative mode, the from-dict loader (escape law, allowlist Reviver, secrets placeholders), the hand-built MCP client adapter (stdio + in-memory, elicitation both ways), the conformance suite every model passes, and the model-profiles registry + CLI.

Files: `server/app/aep/hub.py` (957 lines), `server/app/aep/load.py` (393 lines), `server/app/aep/mcp.py` (723 lines), `server/app/aep/conformance.py` (267 lines)
Suite: `server/tests/test_v0570_hoola_hub.py` (44 tests)

| Upstream feature | Hoola symbol | Proven by |
|---|---|---|
| init_chat_model fixed mode | `app.aep.hub.init_chat_model` | `test_fixed_model_and_provider_kwarg_form` |
| prefix inference + honest unknown refusal | `app.aep.hub.init_chat_model` | `test_prefix_inference_and_unknown_refusal` |
| register_provider extensions | `app.aep.hub.register_provider` | `test_register_provider_extension` |
| ConfigurableModel model-less mode | `app.aep.hub.ConfigurableModel` | `test_model_less_requires_config` |
| per-call config selection + fields filter | `app.aep.hub.ConfigurableModel` | `test_configurable_selects_model_per_call` |
| queued declarative calls | `app.aep.hub.ConfigurableModel` | `test_declarative_calls_queued_until_resolved` |
| with_config pinned + per-call win | `app.aep.hub.ConfigurableModel` | `test_with_config_and_stream_batch_ride_resolution` |
| HouseBrainChatModel injected runner | `app.aep.hub.HouseBrainChatModel` | `test_house_brain_sync_runner_and_no_runner_refusal` |
| the async brain lane | `app.aep.hub.HouseBrainChatModel` | `test_house_brain_async_runner` |
| BYOK invoke + tool-call parse | `app.aep.hub.OpenAICompatChatModel` | `test_byok_invoke_and_tool_call_parse` |
| broken args dropped (finish=length) | `app.aep.hub.OpenAICompatChatModel` | `test_byok_broken_args_dropped_and_finish_length` |
| SSE streaming merge | `app.aep.hub.OpenAICompatChatModel` | `test_byok_stream_sse_merge` |
| bind_tools on the OpenAI wire | `app.aep.hub.OpenAICompatChatModel` | `test_byok_bind_tools_rides_the_openai_wire` |
| standard_params override (misattribution law) | `app.aep.hub.OpenAICompatChatModel` | `test_byok_standard_params_override` |
| BYOK error lanes | `app.aep.hub.OpenAICompatChatModel` | `test_byok_error_lanes` |
| dumpd/load round trip (both lanes) | `app.aep.load.dumpd` | `test_dumpd_load_round_trip_message_lane` |
| dumps/loads JSON string lane | `app.aep.load.loads` | `test_dumps_loads_string_lane` |
| not_implemented marker names the loss | `app.aep.load.SerializedNotImplemented` | `test_not_implemented_marker_names_the_loss` |
| the escape law (lc dicts never instantiate) | `app.aep.load.load` | `test_escape_law_plain_lc_dicts_never_instantiate` |
| allowed_objects gates + crafted-id refusal | `app.aep.load.load` | `test_allowed_objects_gates` |
| lc_secrets placeholders | `app.aep.load.dumpd` | `test_secrets_placeholders` |
| MCP initialize + cursor pagination | `app.aep.mcp.McpClient` | `test_mcp_handshake_pagination_and_tools` |
| MCP tool call + artifact | `app.aep.mcp.McpTool` | `test_mcp_tool_call_content_and_artifact` |
| open object args stay open | `app.aep.mcp.schema_dict_to_model` | `test_mcp_open_object_args_stay_open` |
| MCP image/audio/error lanes | `app.aep.mcp.McpToolError` | `test_mcp_image_audio_and_error_lanes` |
| elicitation both ways | `app.aep.mcp.McpClient` | `test_mcp_elicitation_both_ways` |
| stdio subprocess round trip | `app.aep.mcp.StdioTransport` | `test_stdio_transport_real_subprocess_round_trip` |
| stdio timeout refusal | `app.aep.mcp.StdioTransport` | `test_stdio_timeout_refusal` |
| group mangling + resolve | `app.aep.mcp.McpClientGroup` | `test_mcp_group_mangling_and_resolve` |
| string targets refused at the gate | `app.aep.mcp.load_mcp_tools` | `test_bare_string_targets_refused_at_the_mcp_gate` |
| conformance: every house adapter passes | `app.aep.conformance.assert_conformance` | `test_conformance_every_house_adapter_passes` |
| conformance: broken fails by name | `app.aep.conformance.run_standard_tests` | `test_conformance_broken_model_fails_by_name` |
| model_data_to_profile (models.dev shape) | `app.aep.hub.model_data_to_profile` | `test_model_data_to_profile_mapping` |
| refresh_profiles byte-stable | `app.aep.hub.refresh_profiles` | `test_refresh_profiles_byte_stable` |
| profile diff markdown | `app.aep.hub.summarize_profile_diff` | `test_summarize_profile_diff_markdown` |
| the CLI lanes + the -m entry | `app.aep.hub.main` | `test_cli_lanes` |

