---
type: "AEP evidence"
title: "P4 HOOLA AGENT"
generated: { by: "app.aep.audit/0.600.0" }
sources:
  - repo://server/app/aep/agent.py
  - repo://server/tests/test_v0540_hoola_agent.py
---

create_agent: the agent loop compiled onto the house graph - ToolNode, pending-tool_calls routing, return_direct, structured response, breakpoints on the park seam, checkpointer chat memory.

Files: `server/app/aep/agent.py` (682 lines)
Suite: `server/tests/test_v0540_hoola_agent.py` (56 tests)

| Upstream feature | Hoola symbol | Proven by |
|---|---|---|
| create_agent -> a named compiled graph | `app.aep.agent.create_agent` | `test_create_agent_returns_a_named_compiled_graph` |
| create_react_agent alias | `app.aep.agent.create_react_agent` | `test_default_name_is_agent_and_alias_is_identity` |
| model-only agent (no tools) | `app.aep.agent.create_agent` | `test_no_tools_agent_is_model_only` |
| model string refused (the P7 pointer) | `app.aep.agent.create_agent` | `test_model_string_refused_with_the_p7_pointer` |
| plain callables become tools | `app.aep.agent.create_agent` | `test_plain_callable_becomes_a_tool` |
| model without bind_tools refused at build | `app.aep.agent.create_agent` | `test_model_without_bind_tools_refused_at_build_time` |
| prebound Runnable model lane | `app.aep.agent.create_agent` | `test_prebound_runnable_model_lane` |
| full ReAct loop | `app.aep.agent.create_agent` | `test_full_react_loop` |
| system prompt rides the prompt | `app.aep.agent.create_agent` | `test_system_prompt_rides_the_prompt_never_the_state` |
| parallel tool calls fan-in call order | `app.aep.agent.ToolNode` | `test_parallel_tool_calls_fan_in_call_order` |
| tool error -> error ToolMessage, loop continues | `app.aep.agent.ToolNode` | `test_tool_error_becomes_an_error_toolmessage_and_loop_continues` |
| handle_tool_errors=False reraises | `app.aep.agent.ToolNode` | `test_handle_tool_errors_false_reraises` |
| unknown tool -> honest error ToolMessage | `app.aep.agent.ToolNode` | `test_unknown_tool_name_is_an_honest_error_toolmessage` |
| return_direct ends the walk | `app.aep.agent.ToolNode` | `test_return_direct_tool_ends_the_walk` |
| ToolNode standalone lanes + name override | `app.aep.agent.ToolNode` | `test_toolnode_standalone_state_and_explicit_lanes` |
| response_format -> structured_response | `app.aep.agent.create_agent` | `test_response_format_pydantic_populates_structured_response` |
| response_format after the tool rounds | `app.aep.agent.create_agent` | `test_response_format_runs_only_after_the_tool_rounds` |
| custom state schema rides extra channels | `app.aep.agent.create_agent` | `test_custom_state_schema_rides_extra_channels` |
| checkpointer = chat memory across invokes | `app.aep.agent.create_agent` | `test_checkpointer_gives_chat_memory_across_invokes` |
| interrupt_before/after breakpoints | `app.aep.agent.create_agent` | `test_interrupt_before_tools_parks_then_resumes` |
| a tool may park the walk (interrupt inside) | `app.aep.agent.ToolNode` | `test_a_tool_may_park_the_walk_and_resume_inside_the_tool` |
| agent spans nest under a named root | `app.aep.agent.create_agent` | `test_agent_spans_nest_model_and_tools_under_a_named_root` |
| compiled agent carries checkpointer + store | `app.aep.agent.create_agent` | `test_compiled_agent_carries_checkpointer_and_store` |
| recursion limit configurable per invoke | `app.aep.agent.create_agent` | `test_recursion_limit_configurable_per_invoke` |

