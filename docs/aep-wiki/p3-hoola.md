---
type: "AEP evidence"
title: "P3 HOOLA GRAPH"
generated: { by: "app.aep.audit/0.600.0" }
sources:
  - repo://server/app/aep/graph.py
  - repo://server/tests/test_v0530_hoola_graph.py
---

The state-graph engine: nodes/edges/conditional, fan-out + join barriers, add_messages + AgentState, interrupt/Command park-and-resume, MemorySaver + SqliteSaver - the machine create_agent compiles onto.

Files: `server/app/aep/graph.py` (1152 lines)
Suite: `server/tests/test_v0530_hoola_graph.py` (42 tests)

| Upstream feature | Hoola symbol | Proven by |
|---|---|---|
| StateGraph nodes/edges build-time gates | `app.aep.graph.StateGraph` | `test_add_node_refuses_duplicates_reserved_and_junk` |
| conditional edges + path maps | `app.aep.graph.StateGraph` | `test_conditional_dict_and_positional_path_maps` |
| compile gates (no nodes/entry/bad map) | `app.aep.graph.StateGraph` | `test_compile_refuses_no_nodes_no_entry_and_bad_path_map` |
| plain channels last-value-wins | `app.aep.graph.StateGraph` | `test_plain_channels_are_last_value_wins` |
| reducer channels merge, first seeds | `app.aep.graph.StateGraph` | `test_reducer_channels_merge_and_first_value_seeds` |
| diamond fan-out + join barrier | `app.aep.graph.StateGraph` | `test_diamond_fan_out_join_barrier_runs_once` |
| add_messages semantics | `app.aep.graph.add_messages` | `test_add_messages_semantics` |
| AgentState accumulates messages | `app.aep.graph.AgentState` | `test_agent_state_accumulates_messages_across_nodes` |
| checkpoint every super-step + get_state | `app.aep.graph.BaseCheckpointSaver` | `test_checkpoint_after_every_super_step_and_get_state` |
| MemorySaver isolation + delete | `app.aep.graph.MemorySaver` | `test_memory_saver_thread_isolation_and_delete` |
| SqliteSaver round trip (path lane) | `app.aep.graph.SqliteSaver` | `test_sqlite_saver_round_trip_and_refusals(tmp_path)` |
| SqliteSaver engine lane (the vault way) | `app.aep.graph.SqliteSaver` | `test_sqlite_saver_engine_shape_the_vault_way(tmp_path)` |
| interrupt()/Command park-and-resume | `app.aep.graph.interrupt` | `test_park_shape_and_resume` |
| Command(update) + goto | `app.aep.graph.Command` | `test_command_update_only_and_goto` |
| second interrupt keeps the first answer | `app.aep.graph.GraphInterrupt` | `test_two_interrupts_second_park_keeps_first_answer` |
| resume without a park refuses | `app.aep.graph.GraphInterrupt` | `test_resume_without_a_park_refuses` |
| async nodes + park | `app.aep.graph.StateGraph` | `test_async_nodes_ainvoke_and_park` |
| node spans named by the node | `app.aep.graph.StateGraph` | `test_node_spans_fire_named_by_the_node` |
| recursion limit default + configurable | `app.aep.graph.GraphRecursionError` | `test_recursion_limit_default_and_configurable` |
| config + store ride two-arg nodes | `app.aep.graph.StateGraph` | `test_two_arg_node_receives_config_and_store_rides` |
| update_state rederives next | `app.aep.graph.StateGraph` | `test_update_state_as_node_rederives_next` |

