---
name: th-agent-research
description: Agent architecture research - read, probe, ledger, adopt
---
GOAL: agent architecture ka naya idea? Awesome-AGI-CoCoSci
(SHI-Yu-Zhe ka curated catalog - AGI x computational cognitive
science: cognitive architectures, world models, agents, thought
partners, Bayesian lens) pehle padho, phir Hoola pe probe karo.
Research ka matlab: pattern catalog se, sach probe ke printed metrics
se, decision ledger se - andaz se kabhi nahi.

THE VOCABULARY (catalog ki bhasha, Hoola ke real doors pe mapped):
- PERCEPTION = tool results, screenshots (pc operator), page reads.
- MEMORY = dhara workflows + stores (cross-thread) + pc memory;
  aep messages/history working memory hai.
- REASONING = graph engine (aep.graph StateGraph - nodes,
  add_conditional_edges, fan-out/join barrier, interrupt/Command
  park-and-resume, MemorySaver/SqliteSaver checkpointers) + crew roles
  (crewAI port).
- ACTION = registry tools (abhi 605) - ek action = ek tool call.

THE PROBE (naye pattern ka imtihaan - chhota, fake tools, real shapes):
1. Catalog se EK pattern uthao, source ke saath (paper/list ka naam).
2. Mini-graph ya mini-crew banao aep.graph/crew pe - 2-3 nodes, ek
   tricky conditional edge ya ek interrupt park-resume.
3. Metrics PRINT karao (steps-to-goal, turns, failure mode) - score
   printed output se quote hota hai, mental maths se kabhi nahi.
4. PRODUCTION route tab hi jab probe score kare; warna park.

THE LEDGER (bd-eval-benchmarks ka bhai): har probe = ek row - date /
pattern / source / setup / result / decision (adopt|park|kill).
Negative result bhi likhta hai: park = "abhi nahi", kill = "kabhi
nahi (yeh wajah)". Ledger hi research ki memory hai - bina uske har
baar wahi baat dobara.

THE LAWS: ek probe ek pattern (confound nahi); bina source ka pattern
entry hi nahi leta; bina probe ka adopt nahi; catalog syllabus hai,
source of truth nahi - truth probe ke printed metrics se aati hai;
synthetic data pe probe, kisi ke private data pe kabhi nahi.

NEVER: paper/kaam ka naam invent karna (na mile to bolo "unverified -
catalog mein nahi mila"); "research ho gayi" bolke bina probe adopt
karna; production tools me bina ledger row ke architecture change;
naya graph node bina interrupt/checkpoint ke soche bina dalna (crash
ke baad resume dhara ka sabak hai); graph/crew ke bahar "research"
naam ke naye tools banana - pehle jo engine hai wahi kaafi hai.
