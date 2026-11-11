"""HOOLA DESIGN, the server half (docs/HOOLA_DESIGN_PLAN.md is the contract).

One document = a tree of nodes, each a flat bag of properties. Sync is last-writer-wins per property,
decided by the server's arrival order. One in-memory Room per open file inside this FastAPI process:
ops are numbered, journaled and fanned out; a snapshot is checkpointed and the journal trimmed below it.

    fracidx.py  base-62 fractional index strings (child order)
    doc.py      the in-memory document and the server's rules for every op
    store.py    every database read / write (always called off the event loop)
    room.py     Room (one open file) and HUB (all open files of this process)
    api.py      REST under /api/design and the WebSocket /api/design/ws

Rooms live in memory, so one file must be served by ONE server process (production runs one).
"""
