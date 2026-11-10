"""v0.610.0 HOOLA ADOPT - the product's first live lane ON the AEP.

Owner: 'CURRENTLY HOOLA DONT USE AEP IT NEED USER AUTH'. The AEP train (P1-P8)
is a library layer - inert by law, adopted lane-by-lane. THIS module is the
first adoption: one real turn of HOOLA run ON the AEP - create_agent over the
house graph (P4), the production brain injected through hoola_brain_factory
(P7 - the lazy lane imports app.agent.llm only when CALLED), the unified
middlewares riding the calls (P5), every span landing in the run-tree tracer
(P2, process store + the vault sink when aep_trace is flipped), chat memory
through the SqliteSaver checkpointer on the conversation's thread (P3 - the
CHECKPOINT-MERGE law).

THE AUTH LAW: the lane is served by POST /api/aep/turn/{conversation_id}
behind the product's user auth (require_key + current_tenant). A signed-in
product user resolves to their own tenant; the legacy API key stays the owner
override; anonymous callers get 401 the moment the server has a key. The
conversation must belong to the caller's tenant (_conv_or_404).

THE INERTNESS LAW held: importing this module spawns nothing, reads no env,
touches no files - the brain import, the checkpointer file and the tracer
attach all happen INSIDE aep_turn(), per call. The production loop
(santosh.run_turn) is untouched - old APKs keep working; this lane is opt-in
per call, never a silent behavior change.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..aep import tracers
from ..aep import vault_sink as _vault
from ..aep.agent import create_agent
from ..aep.graph import SqliteSaver
from ..aep.hub import hoola_brain_factory
from ..aep.messages import AIMessage, BaseMessage, HumanMessage
from ..aep.middleware import CuratorMiddleware, NudgeMiddleware

LANE_NAME = "hoola-aep-turn"


def map_history(history: list[dict]) -> list[BaseMessage]:
    """Product history rows ({role, content: str | block list}) -> AEP messages.
    Non-text blocks (cards, tool results) collapse to their text lines - the
    AEP turn rides the same conversation WORDS the model would see; a row with
    no text at all is skipped (a card-only bubble carries no words)."""
    out: list[BaseMessage] = []
    for m in history or []:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        c = m.get("content")
        if isinstance(c, str):
            text = c
        else:
            parts = []
            for b in c or []:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text"):
                    parts.append(str(b["text"]))
                elif isinstance(b, dict) and b.get("type") == "tool_result":
                    parts.append(str(b.get("text") or b.get("content") or ""))
            text = "\n".join(p for p in parts if p)
        if text:
            out.append(HumanMessage(content=text) if role == "user" else AIMessage(content=text))
    return out


@dataclass
class AepTurn:
    """What one AEP turn hands back to the route: the reply words plus the
    honest handles (the run-tree id, the thread, what rode the call)."""

    reply: str
    run_id: str | None = None
    thread_id: str = ""
    model: str = "auto"
    middleware: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    ms: int = 0


def build_agent(brain: str = "auto", *, runner: Callable | None = None,
                tools: Sequence[Any] | None = None,
                middleware: Sequence[Any] | None = None,
                system: str | None = None, checkpointer: Any = None,
                name: str = LANE_NAME):
    """Compile the AEP agent for one lane call. The default middleware ride is
    Nudge + Curator (her words stay hers - a muted nudge adds nothing; the
    curator folds duplicate tool noise); Delegate / SkillsPrimer stay opt-in
    (they need a worker / primers the caller must hand over)."""
    model = hoola_brain_factory(brain, runner=runner)
    mws = list(middleware) if middleware is not None else [NudgeMiddleware(), CuratorMiddleware()]
    return create_agent(model, tools=list(tools or []), system_prompt=system,
                        middleware=mws, checkpointer=checkpointer, name=name)


def default_checkpointer(path: str):
    """A per-process SqliteSaver over one file - chat memory that survives the
    turn (the P3 CHECKPOINT-MERGE law: a dict input on a checkpointed thread
    merges through add_messages)."""
    return SqliteSaver(path=path)


async def aep_turn(conversation_id: str, user_text: str, tenant_id: str, *,
                   brain: str = "auto", runner: Callable | None = None,
                   tools: Sequence[Any] | None = None,
                   middleware: Sequence[Any] | None = None,
                   system: str | None = None, history: list[dict] | None = None,
                   checkpointer: Any = None) -> AepTurn:
    """One turn of HOOLA ON the AEP, end to end.

    history    : the product's pre-turn conversation rows (already loaded by
                 the route BEFORE the user row is saved) - mapped and seeded
                 into state so even a fresh thread sees the conversation.
    checkpointer: pass a SqliteSaver to get real cross-turn memory; None runs
                 a stateless turn (history still rides).
    """
    t0 = time.time()
    agent = build_agent(brain=brain, runner=runner, tools=tools, middleware=middleware,
                        system=system, checkpointer=checkpointer)
    messages = map_history(history or []) + [HumanMessage(content=user_text)]
    cfg: dict[str, Any] = {"configurable": {"thread_id": conversation_id}}
    tracer = tracers.global_tracer()
    cfg["callbacks"] = [tracer]
    if _vault.trace_enabled():
        _vault.attach_vault_sink(tracer, tenant=tenant_id, conv=conversation_id)
    result = await agent.ainvoke({"messages": messages}, cfg)
    reply = ""
    state_messages = result.get("messages", []) if isinstance(result, dict) else []
    for m in reversed(state_messages):
        if getattr(m, "type", "") == "ai":
            reply = (m.text or "").strip()
            break
    run_id = None
    recent = tracers.GLOBAL_STORE.recent(1)
    if recent:
        run_id = recent[-1].id
    tool_names = [getattr(t, "name", type(t).__name__) for t in (tools or [])]
    mws = list(middleware) if middleware is not None else [NudgeMiddleware(), CuratorMiddleware()]
    return AepTurn(reply=reply, run_id=run_id, thread_id=conversation_id,
                   model=brain, middleware=[type(m).__name__ for m in mws],
                   tools=tool_names, ms=int((time.time() - t0) * 1000))
