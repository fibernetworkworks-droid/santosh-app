"""HOOLA SWARM (v0.478.0) - self-spawning subagents for parallel work, Hermes's delegation ported.

ONE tool, `delegate_task`: the parent hands N task prompts; each runs as a BOUNDED child agent
on the SAME model path the parent turn uses (santosh._call_brain - GLM/OmniRoute or Claude, no
new plumbing), with the SAME tool surface MINUS a hard deny set, and every child tool call rides
santosh._run_tool - the single funnel - so scrub, timeout, the harness log and CODER CAPTURE all
see exactly what the children did. Results return merged as one tool result.

Hermes's shape, kept and adapted:
  MAX_DEPTH = 1         flat by default: parent (0) -> child (1); a child can NEVER spawn another
                        delegate_task (Hermes's delegate_tool_config.py rule, hard here)
  concurrency cap       Hermes default 10 children; Hoola is a voice box on a modest VPS:
                        coder_delegate_max_children default 3, which is ALSO the per-call cap
                        (Hermes separates oneshot_max_children=2 from concurrent=10; one knob is
                        the cost-right shape here) - the too-many-tasks rejection message keeps
                        Hermes's wording
  child timeout         Hermes DEFAULT_CHILD_TIMEOUT = None (unbounded is fine for a CLI); a
                        voice box bounds every child: coder_delegate_timeout_s default 120 s,
                        a timed-out child returns ok=False with what it had
  money never moves     Hermes children get the parent's full surface; Hoola's children are
                        DENIED the approval/send family at dispatch: delegate_task (depth),
                        confirm_send (campaign sends), haan_karo (approval cards - voice can
                        never approve money anyway), pc_do (a child must not start a long PC
                        job that outlives it)
  capture sees all      children share the parent's Ctx (tenant + conversation), so the coder
                        funnel tags every child tool call into the same session memory
  fail-open             a child error is ONE failed result; the batch still returns
  kill switch           coder_delegate (default OFF - bake on the VPS, then flip); voice calls
                        never see the tool at all (the VOICE_TOOL_NAMES allowlist)
"""
from __future__ import annotations

import asyncio
import logging
import time

log = logging.getLogger("coder.delegate")

CHILD_SYSTEM = (
    "You are ONE of Santosh's parallel workers. A main agent handed you ONE task; other workers "
    "are handling the others. Do exactly this task, use the tools you need, and finish with a "
    "short final answer (the worker's report the main agent will merge). You cannot ask the user "
    "anything - no greetings, no questions back, just the work and the report. English report.")

# v0.484 the skills reach: a worker gets the parent's matched LEARNED SKILLS lines in its own
# system prompt (inject.child_skills, <=400 chars) and reads the full skill itself via
# skill_manage - the read-before-follow law survives delegation.
CHILD_SKILLS_BUDGET = 400

CHILD_DENIED = frozenset({"delegate_task", "confirm_send", "haan_karo", "pc_do"})
CHILD_MAX_ITERS = 6
CHILD_MAX_TOKENS = 2000
PROMPT_MAX = 4000


def _settings():
    try:
        from ..config import get_settings
        return get_settings()
    except Exception:
        return None


def _cap() -> int:
    st = _settings()
    try:
        return max(1, int(getattr(st, "coder_delegate_max_children", 3) or 3))
    except Exception:
        return 3


def _timeout_s() -> int:
    st = _settings()
    try:
        return max(10, int(getattr(st, "coder_delegate_timeout_s", 120) or 120))
    except Exception:
        return 120


def stats() -> dict:
    return {"children_denied": sorted(CHILD_DENIED), "child_max_iters": CHILD_MAX_ITERS,
            "child_max_tokens": CHILD_MAX_TOKENS}


# ---------------------------------------------------------------- the child runner

def _child_specs() -> list[dict]:
    """The child's tool surface: every registered spec MINUS the deny set (depth cap + money)."""
    from ..agent.tools import TOOLS
    return [dict(t) for t in TOOLS if t.get("name") and t["name"] not in CHILD_DENIED]


def _blocks_text(blocks: list[dict]) -> str:
    return "".join(b.get("text", "") for b in (blocks or []) if b.get("type") == "text").strip()


async def run_child(ctx, settings, task: dict, task_index: int) -> dict:
    """One bounded child: task in, report out. Every tool call rides santosh._run_tool."""
    from ..agent import llm
    from ..agent.santosh import _call_brain, _run_tool
    prompt = str(task.get("prompt") or "").strip()[:PROMPT_MAX]
    label = str(task.get("label") or f"task-{task_index + 1}")[:80]
    t0 = time.time()
    brain = llm.cheap_brain()
    system = CHILD_SYSTEM
    try:                                     # v0.484 matched skills ride in, fail-open
        from . import inject as _inj
        sk = _inj.child_skills(ctx.tenant_id, prompt, budget=CHILD_SKILLS_BUDGET)
        if sk:
            system = CHILD_SYSTEM + "\n\n" + sk
    except Exception:
        pass
    history: list[dict] = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    specs = _child_specs()
    tool_calls = 0
    try:
        for _ in range(CHILD_MAX_ITERS):
            blocks, stop = await _call_brain(brain, system, history, settings,
                                             tools=specs, max_tokens=CHILD_MAX_TOKENS)
            text = _blocks_text(blocks)
            if stop != "tool_use" or not any(b.get("type") == "tool_use" for b in blocks or []):
                return {"label": label, "ok": True, "text": text or "(no report)",
                        "tool_calls": tool_calls, "seconds": round(time.time() - t0, 1)}
            history.append({"role": "assistant", "content": blocks})
            results = []
            for b in blocks:
                if b.get("type") != "tool_use":
                    continue
                name, args = b.get("name", ""), b.get("input") or {}
                if name in CHILD_DENIED:       # the depth cap + money floor, at dispatch
                    results.append({"type": "tool_result", "tool_use_id": b.get("id", ""),
                                    "content": f"DENIED: {name} is not available to a worker "
                                               f"(a worker cannot delegate, send, approve or start PC jobs). "
                                               f"Finish with what you have."})
                    continue
                tool_calls += 1
                try:
                    out = await _run_tool(name, args, ctx, settings)
                    import json as _json
                    try:
                        line = _json.dumps(out, ensure_ascii=False, default=str)[:4000]
                    except Exception:
                        line = str(out)[:4000]
                except Exception as e:         # one failed tool never kills the child
                    line = f"error: {type(e).__name__}: {str(e)[:300]}"
                results.append({"type": "tool_result", "tool_use_id": b.get("id", ""),
                                "content": line})
            history.append({"role": "user", "content": results})
        return {"label": label, "ok": True,
                "text": "(stopped at the worker iteration budget; partial work above)",
                "tool_calls": tool_calls, "seconds": round(time.time() - t0, 1)}
    except asyncio.CancelledError:
        raise                                   # the caller's timeout owns cancellation
    except Exception as e:
        return {"label": label, "ok": False, "text": f"worker failed: {type(e).__name__}: {str(e)[:300]}",
                "tool_calls": tool_calls, "seconds": round(time.time() - t0, 1)}


# ---------------------------------------------------------------- the tool

DELEGATE_SCHEMA = {
    "name": "delegate_task",
    "description": (
        "Split work across PARALLEL worker agents: each task prompt runs as its own bounded worker "
        "with the same tools (minus delegation, sends, approvals and PC jobs), and the reports come "
        "back merged. Use for INDEPENDENT chunks (compare three websites, draft two variants, look "
        "up several things at once). Max 3 tasks per call; each worker is capped at 2 minutes and "
        "6 tool rounds. Tasks must not need each other's output. English prompts work best."),
    "input_schema": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "description": "One entry per parallel worker (max 3). Independent tasks only.",
                "items": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string",
                                   "description": "The complete task for ONE worker, self-contained"},
                        "label": {"type": "string",
                                  "description": "Short name for the report, e.g. 'site-a'"},
                    },
                    "required": ["prompt"],
                },
            },
        },
        "required": ["tasks"],
    },
}

DELEGATE_TOOLS = [DELEGATE_SCHEMA]
DELEGATE_LABELS = {"delegate_task": "Kaarobar tez karne ke liye madadgar bhej raha hoon"}
DELEGATE_HANDLERS: dict = {"delegate_task": None}   # set below


async def delegate_task(ctx, tasks=None, **_):
    """The swarm entry: validate, spawn bounded children in parallel, merge the reports."""
    from ..config import get_settings
    st = get_settings()
    if not getattr(st, "coder_enabled", True) or not getattr(st, "coder_delegate", False):
        return {"error": "delegation is switched off (coder_delegate)"}
    if not isinstance(tasks, list) or not tasks:
        return {"error": "tasks must be a non-empty array."}
    cap = _cap()
    if len(tasks) > cap:
        return {"error": f"Too many tasks: {len(tasks)} provided, but max_concurrent_children "
                         f"is {cap}. Merge related work or run the rest in another call."}
    clean: list[dict] = []
    for i, t in enumerate(tasks):
        if not isinstance(t, dict) or not str(t.get("prompt") or "").strip():
            return {"error": f"tasks[{i}] needs a prompt."}
        clean.append({"prompt": str(t.get("prompt"))[:PROMPT_MAX],
                      "label": str(t.get("label") or f"task-{i + 1}")[:80]})
    sem = asyncio.Semaphore(cap)

    async def _one(i: int, t: dict) -> dict:
        async with sem:
            try:
                return await asyncio.wait_for(run_child(ctx, st, t, i), timeout=_timeout_s())
            except asyncio.TimeoutError:
                return {"label": t["label"], "ok": False,
                        "text": f"worker timed out after {_timeout_s()}s", "tool_calls": 0,
                        "seconds": _timeout_s()}
            except Exception as e:              # noqa: BLE001 - one child never sinks the batch
                return {"label": t["label"], "ok": False,
                        "text": f"worker crashed: {type(e).__name__}: {str(e)[:200]}",
                        "tool_calls": 0, "seconds": 0}

    outs = await asyncio.gather(*(_one(i, t) for i, t in enumerate(clean)))
    results = list(outs)
    return {"ok": all(r.get("ok") for r in results), "results": results,
            "parallel": len(results) > 1, "children": len(results)}


DELEGATE_HANDLERS["delegate_task"] = delegate_task
