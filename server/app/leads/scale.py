"""v0.544.0 P4 SCALE - country-scale runs have two needs, both answered with code the house already has.

1. THE STORE ON POSTGRES. Country-scale (the plan's 20,000 rows/day per tenant) is a Postgres job, not a
   SQLite one. The law already exists (db.py: "SQLite by default; set DATABASE_URL to a postgresql+psycopg URL
   in production"; v0.390 dbmove moves her DB checked and repeatable; the HOOLA_TEST_PG convention runs the
   whole suite on Postgres). What P4 adds is the HONEST ANSWER to "kis par khada hai ye store": store_backend()
   names the engine the leads tables are actually on and what country-scale needs - it never claims Postgres
   when the engine is SQLite.

2. ENRICHMENT FANNED OUT. The P2 pass read rows one at a time; at scale that is the long pole. enrich_fanout()
   runs the SAME per-row body across the HOOLA GRAPH (app/aep/graph.py, v0.530): START -> dispatch -> STATIC
   fan-out edges to K chunk nodes (the graph's static multi-edge fan-out - the map case it honestly covers) ->
   the JOIN node, which the graph runs only when ALL chunks have run (the join barrier - every row answered
   before anything is folded). Concurrency is bounded: the chunk nodes share one Semaphore, so at most
   max_in_flight site passes are in flight at any moment (politeness stays per-site 1 req/s inside
   enrich.site_pass - different sites in parallel, the same site never). Store writes stay OUT of the graph:
   the walk computes, the barrier joins, and the service applies the results ONE WRITER AT A TIME after the
   walk (SQLite-safe, and the same provenance path as the serial pass)."""
from __future__ import annotations

import asyncio
import math
import time
from typing import Annotated, Any, Awaitable, Callable, TypedDict

from operator import add as _add

FANOUT_CHUNKS = 4                       # the static fan-out: K chunk nodes off the dispatch node


class FanState(TypedDict):
    """The graph state: chunk nodes APPEND their per-row results (operator.add reducer), join counts them."""
    results: Annotated[list, _add]
    chunks: list
    joined: int


def store_backend() -> dict[str, Any]:
    """Which engine the leads store is on right now, said honestly (the status card reads this)."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    name = eng.dialect.name if eng is not None else "sqlite"
    pg = name == "postgresql"
    return {"engine": name, "country_scale": pg,
            "note": ("Postgres (DATABASE_URL) - the backend for country-scale runs."
                     if pg else
                     "SQLite - fine for running; for country-scale (20,000 rows/day) set DATABASE_URL to "
                     "postgresql+psycopg:// (python -m app.dbmove --to ...). The leads tables "
                     "self-heal on the new engine too (models.ensure_tables).")}


async def enrich_fanout(rows: list, compute: Callable[[Any], Awaitable[dict | None]],
                        max_in_flight: int = 4, chunks: int = FANOUT_CHUNKS) -> dict[str, Any]:
    """The fan-out pass over `rows` with the graph's join barrier. `compute(row)` is the per-row body (async,
    NO store writes). Returns every non-None result, the chunk count and the bound - the card names them.

    Honest shape: the walk runs the chunk nodes of one super-step in order, so the chunks are waves; the
    PARALLELISM is the bounded gather inside each chunk (at most max_in_flight computes in flight, shared
    Semaphore); the BARRIER is the graph's own join law (join runs only when ALL chunk nodes ran), and the
    caller folds only after the walk returns."""
    from ..aep.graph import END, START, StateGraph

    rows = list(rows or [])
    if not rows:
        return {"results": [], "chunks": 0, "max_in_flight": max(1, int(max_in_flight or 4)), "seconds": 0.0}
    sem = asyncio.Semaphore(max(1, int(max_in_flight or 4)))
    k = max(1, min(int(chunks or FANOUT_CHUNKS), len(rows)))
    size = math.ceil(len(rows) / k)
    slices = [rows[i * size:(i + 1) * size] for i in range(k)]

    async def _bounded(row):
        async with sem:
            return await compute(row)

    def make_chunk(sl):
        async def _chunk(state, config=None):
            out = await asyncio.gather(*[_bounded(r) for r in sl])
            return {"results": [x for x in out if x is not None]}
        return _chunk

    g = StateGraph(FanState)
    g.add_node("dispatch", lambda state, config=None: {"chunks": [len(s) for s in slices]})
    for i, sl in enumerate(slices):
        g.add_node(f"chunk_{i}", make_chunk(sl))
        g.add_edge("dispatch", f"chunk_{i}")            # the STATIC fan-out: K edges, one super-step
    g.add_node("join", lambda state, config=None: {"joined": len(state.get("results") or [])})
    for i in range(len(slices)):
        g.add_edge(f"chunk_{i}", "join")                # the JOIN BARRIER: all parents before the fold
    g.add_edge(START, "dispatch")
    g.add_edge("join", END)
    t0 = time.monotonic()
    final = await g.compile().ainvoke({"results": []})
    return {"results": list(final.get("results") or []), "chunks": k,
            "max_in_flight": max(1, int(max_in_flight or 4)), "seconds": round(time.monotonic() - t0, 3)}
