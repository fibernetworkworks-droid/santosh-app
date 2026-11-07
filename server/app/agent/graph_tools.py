"""v0.496.0 CODE GRAPH tools - Graphify as a read-only way to understand a GitHub repo's structure.

  graph_build  map a repo (owner/name or github.com link) into a knowledge graph (local AST, no model call)
  graph_ask    ask the built graph: query / path / explain / affected / god_nodes
  graph_list   the repos she has already mapped

For READING how code fits together (who calls what, what breaks if X changes). To CHANGE code use Developer Sahayak.
"""
from __future__ import annotations

import asyncio
from typing import Any

from .. import codegraph as cg
from .tools import Ctx, ToolError


def _masked(v: Any) -> Any:
    from ..operator.browser import mask_ids
    if isinstance(v, str):
        return mask_ids(v)
    if isinstance(v, dict):
        return {k: _masked(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_masked(x) for x in v]
    return v


GRAPH_TOOLS = [
    {"name": "graph_build",
     "description": (
         "Map a GitHub repo into a code knowledge graph (functions, classes, imports, calls, communities) with Graphify. "
         "Local AST parsing: no model call, free. Use FIRST when she wants to understand a codebase's structure, "
         "dependencies or call flow ('is repo ka naksha banao', 'map this codebase'). Takes a minute or two; her private "
         "repos work through her Developer Sahayak token. Then use graph_ask. NOT for changing code (Developer Sahayak)."),
     "input_schema": {"type": "object", "properties": {
         "repo": {"type": "string", "description": "owner/name or https://github.com/owner/name"},
         "ref": {"type": "string", "description": "Optional branch or tag (default: the repo's default branch)"}},
         "required": ["repo"]}},
    {"name": "graph_ask",
     "description": (
         "Ask a built code graph. kind=query: a plain-language question ('what connects auth to the database?'). "
         "kind=path: how two things connect (a, b). kind=explain: one class/function and its links (a). "
         "kind=affected: what breaks if a changes (a, depth). kind=god_nodes: the most connected hubs. "
         "Use instead of grepping many files to learn structure. Every link is tagged EXTRACTED (in the source) or "
         "INFERRED (resolved) - say which when it matters. The repo must be mapped first with graph_build."),
     "input_schema": {"type": "object", "properties": {
         "repo": {"type": "string", "description": "owner/name of a repo already mapped"},
         "kind": {"type": "string", "enum": list(cg.KINDS)},
         "question": {"type": "string", "description": "For kind=query"},
         "a": {"type": "string", "description": "Node name for path/explain/affected (the 'from' for path)"},
         "b": {"type": "string", "description": "The 'to' node for path"},
         "depth": {"type": "integer", "description": "Traversal depth 1-6 (default 2)"},
         "budget": {"type": "integer", "description": "Answer size cap in tokens (default 2000, max 6000)"}},
         "required": ["repo", "kind"]}},
    {"name": "graph_list",
     "description": "List the repos she has already mapped with graph_build (when, how many nodes and links).",
     "input_schema": {"type": "object", "properties": {}}},
]

GRAPH_LABELS = {"graph_build": "Repo ka code-naksha bana raha hoon",
                "graph_ask": "Code ke naksha mein dhoondh raha hoon",
                "graph_list": "Bane hue code-nakshe dekh raha hoon"}


async def graph_build(ctx: Ctx, repo: str = "", ref: str = "", **_):
    try:
        return _masked(await asyncio.to_thread(cg.build, ctx.tenant_id, repo, ref))
    except cg.GraphError as e:
        raise ToolError(str(e))


async def graph_ask(ctx: Ctx, repo: str = "", kind: str = "query", question: str = "", a: str = "", b: str = "",
                    depth: int = 2, budget: int = 2000, **_):
    try:
        return _masked(await asyncio.to_thread(cg.ask, ctx.tenant_id, repo, kind, question, a, b, depth, budget))
    except cg.GraphError as e:
        raise ToolError(str(e))


async def graph_list(ctx: Ctx, **_):
    rows = await asyncio.to_thread(cg.list_graphs, ctx.tenant_id)
    return {"graphs": rows, "count": len(rows), "ready": bool(cg.enabled() and cg.binary())}


GRAPH_HANDLERS = {"graph_build": graph_build, "graph_ask": graph_ask, "graph_list": graph_list}
