---
name: th-agent-research
description: Agent architecture research - read, probe, ledger, adopt
when_to_use: agent architecture, ai research, cognitive architecture, world model, new agent idea, research paper
---
GOAL: a new idea for agent architecture? Read Awesome-AGI-CoCoSci
first (SHI-Yu-Zhe's curated catalog - AGI x computational cognitive
science: cognitive architectures, world models, agents, thought
partners, the Bayesian lens), then probe it on Hoola. Research means:
the pattern from the catalog, the truth from the probe's printed
metrics, the decision from the ledger - never from a guess.

THE VOCABULARY (the catalog's language, mapped onto Hoola's real
doors):
- PERCEPTION = tool results, screenshots (pc operator), page reads.
- MEMORY = dhara workflows + stores (cross-thread) + pc memory;
  aep messages / history are the working memory.
- REASONING = the graph engine (aep.graph StateGraph - nodes,
  add_conditional_edges, fan-out / join barrier, interrupt / Command
  park-and-resume, MemorySaver / SqliteSaver checkpointers) + crew
  roles (the crewAI port).
- ACTION = registry tools (605 today) - one action = one tool call.

THE PROBE (the test of a new pattern - small, fake tools, real
shapes):
1. Take ONE pattern from the catalog, with its source (the name of
   the paper / list).
2. Build a mini-graph or mini-crew on aep.graph / crew - 2-3 nodes,
   one tricky conditional edge or one interrupt park-resume.
3. Have the metrics PRINTED (steps-to-goal, turns, failure mode) - a
   score is quoted from printed output, never from mental maths.
4. The PRODUCTION route only when the probe scores; otherwise park.

THE LEDGER (the sibling of bd-eval-benchmarks): every probe = one
row - date / pattern / source / setup / result / decision
(adopt|park|kill). A negative result is written too: park = "not
now", kill = "never (for this reason)". The ledger is the memory of
the research - without it the same thing is done again every time.

THE LAWS: one probe, one pattern (no confounds); a pattern with no
source does not get an entry; no adopt without a probe; the catalog
is the syllabus, not the source of truth - the truth comes from the
probe's printed metrics; probe on synthetic data, never on anyone's
private data.

NEVER: invent the name of a paper / work (if it is not found say
"unverified - not found in the catalog"); say "research is done" and
adopt without a probe; an architecture change in production tools
without a ledger row; add a new graph node without thinking about
interrupt / checkpoint (resume after a crash is the lesson of
dhara); build new tools named "research" outside the graph / crew -
the engine that exists is enough.

ALSO ASKED AS (Hinglish asks this skill answers): agent architecture ka naya
pattern research aur probe karo, naya agent idea try karna hai
