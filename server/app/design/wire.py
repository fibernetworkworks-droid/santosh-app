"""D9b speed: the compact op encoding `c1` and the page-by-page cut of a big document (contract section 8, D9b).

c1 (JSON text whose top level is an ARRAY, so it can never be mistaken for a JSON frame, which is an object):
    client -> server ops   [1, n, [op, ...]]
    server -> client ops   [2, seq, by, [op, ...]]
    server -> client ack   [3, n, seq, [rejected index, ...]]   (+ a 5th element [ex index, ...] when there are any)
    op                     [id]                      delete (the node and its subtree)
                           [id, k, v, k, v, ...]     set; k = an index into KEYS, or the property name itself when it
                                                     is not in KEYS (forward compatible); k = -1 alone = an empty set;
                                                     the pair (-2, 1) = the op's `ex` mark
KEYS is FIXED (it is the same list in hd-net.js, a test holds them equal): one table for every connection, so the
server encodes a batch ONCE for everyone who speaks c1. Numbers stay JSON numbers: their decimal text is already
shorter than 8 bytes of a float, and a value must come back bit for bit (last writer wins on exact values).

Page by page: `cut(doc, want)` copies, on the event loop and without serialising anything, the root, every
top-level node (the pages) and the whole subtrees of the wanted pages plus the pages their instances' components
live on; a worker thread turns the copy into the `init` / `page` frame. A copy is consistent because the room is
the only writer and runs on the loop, and `Doc` replaces values, never changes them in place (doc.py).
"""
from __future__ import annotations

from typing import Any, Iterable

from .doc import ROOT, Doc, dumps

KEYS = (
    "type", "parent", "idx", "name", "x", "y", "w", "h", "rot", "flipH", "flipV", "visible", "locked", "opacity",
    "blend", "mask", "fills", "strokes", "strokeWeight", "strokeAlign", "strokeCap", "strokeJoin", "dash", "radius",
    "effects", "clip", "layout", "grids", "bool", "sizeH", "sizeV", "layoutPos", "minW", "maxW", "minH", "maxH",
    "cons", "sides", "ratio", "path", "fillRule", "chars", "font", "fontSize", "fontWeight", "italic", "lineHeight",
    "letterSpacing", "align", "alignV", "autoResize", "decoration", "textCase", "runs", "comp", "ov", "desc", "styles",
    "vars", "modes", "fillStyle", "textStyle", "effectStyle", "bind", "reactions", "protoStart", "scroll", "fixed",
    "exports", "bg", "guides",
)
KEY_NO = {k: i for i, k in enumerate(KEYS)}
ENCODINGS = ("json", "c1")


# ------------------------------------------------------------------------------------------------ c1
def enc_op(op: dict) -> list:
    nid = op.get("id")
    if op.get("del"):
        return [nid]
    out: list[Any] = [nid]
    props = op.get("p") or {}
    for key, value in props.items():
        out.append(KEY_NO.get(key, key))
        out.append(value)
    if op.get("ex"):
        out.append(-2)
        out.append(1)
    if len(out) == 1:
        out.append(-1)
    return out


def dec_op(arr: Any) -> dict | None:
    """One c1 op -> the JSON op; None = not an op (the room refuses it like any malformed op)."""
    if not isinstance(arr, list) or not arr or not isinstance(arr[0], str):
        return None
    if len(arr) == 1:
        return {"id": arr[0], "del": 1}
    if len(arr) % 2 == 0 and arr[1:] != [-1]:
        return None
    props: dict[str, Any] = {}
    op: dict[str, Any] = {"id": arr[0], "p": props}
    for i in range(1, len(arr) - 1, 2):
        key = arr[i]
        if type(key) is int:
            if key == -2:
                op["ex"] = 1
                continue
            if not 0 <= key < len(KEYS):
                return None
            key = KEYS[key]
        elif not isinstance(key, str):
            return None
        props[key] = arr[i + 1]
    return op


def ops_frame(seq: int, by: int, ops: list[dict]) -> str:
    return dumps([2, seq, by, [enc_op(op) for op in ops]])


def ack_frame(n: int, seq: int, rejected: list[int], ex: list[int]) -> str:
    return dumps([3, n, seq, rejected, ex] if ex else [3, n, seq, rejected])


def from_c1(frame: list) -> dict | None:
    """A c1 frame from a browser -> the JSON frame the room reads; None = not one this server knows."""
    if len(frame) == 3 and frame[0] == 1 and type(frame[1]) is int and isinstance(frame[2], list):
        return {"t": "ops", "n": frame[1], "ops": [dec_op(a) for a in frame[2]]}
    return None


# ------------------------------------------------------------------------------------------------ pages
def top_of(doc: Doc, nid: str) -> str | None:
    """The top-level node (a page) that `nid` is on; None = not in the tree."""
    nodes, cur, steps = doc.nodes, nid, len(doc.nodes) + 1
    while cur is not None and steps > 0:
        node = nodes.get(cur)
        if node is None:
            return None
        parent = node.get("parent")
        if parent == ROOT:
            return cur
        cur = parent if isinstance(parent, str) else None
        steps -= 1
    return None


def _comp_refs(node: dict) -> Iterable[str]:
    comp = node.get("comp")
    if isinstance(comp, str):
        yield comp
    ov = node.get("ov")
    if isinstance(ov, dict):
        for value in ov.values():
            if isinstance(value, dict) and isinstance(value.get("comp"), str):
                yield value["comp"]


def subtree(doc: Doc, pid: str, out: dict, refs: set | None = None) -> None:
    """Copy the node `pid` and everything under it into `out` (shallow copies: values are never changed in place)."""
    nodes, kids, stack = doc.nodes, doc._kids, [pid]       # noqa: SLF001 - the room's own document
    while stack:
        cur = stack.pop()
        node = nodes.get(cur)
        if node is None:
            continue
        out[cur] = node.copy()
        if refs is not None and node.get("type") == "INSTANCE":
            refs.update(_comp_refs(node))
        below = kids.get(cur)
        if below:
            stack.extend(below)


def pages(doc: Doc) -> list[str]:
    return [c for c in doc.children(ROOT)]


def closure(doc: Doc, first: list[str], have: set | frozenset = frozenset()) -> tuple[list[str], dict[str, dict]]:
    """The pages to send for `first`, plus the pages the components of their instances are on (unless `have`);
    returns (page ids in sending order - dependencies first, {page id: copied subtree})."""
    order: list[str] = []
    cuts: dict[str, dict] = {}
    todo = [p for p in first]
    while todo:
        pid = todo.pop(0)
        if pid in cuts:
            continue
        refs: set[str] = set()
        part: dict = {}
        subtree(doc, pid, part, refs)
        cuts[pid] = part
        order.append(pid)
        for ref in refs:
            top = top_of(doc, ref)
            if top is not None and top not in cuts and top not in have and top not in todo:
                todo.append(top)
    deps = [p for p in order if p not in first]
    return deps + [p for p in order if p in first], cuts


def cut(doc: Doc, want: list[str]) -> tuple[dict, list[str], list[str]]:
    """The partial init document: (nodes, the top-level ids sent whole, the top-level ids NOT sent)."""
    tops = pages(doc)
    wanted = [p for p in want if p in doc.nodes and doc.nodes[p].get("parent") == ROOT]
    if not wanted:
        wanted = [next((p for p in tops if doc.nodes[p].get("type") == "PAGE"), tops[0])] if tops else []
    order, cuts = closure(doc, wanted)
    nodes = {ROOT: doc.nodes[ROOT].copy()}
    for p in tops:
        nodes[p] = doc.nodes[p].copy()
    for part in cuts.values():
        nodes.update(part)
    sent = set(order)
    return nodes, order, [p for p in tops if p not in sent]


def page_counts(nodes: dict[str, dict]) -> dict[str, int]:
    """Worker thread: how many nodes each top-level node holds (itself included), from a copy of the document."""
    parent_of = {nid: n.get("parent") for nid, n in nodes.items()}
    top: dict[str, str | None] = {}
    counts: dict[str, int] = {}
    for nid in nodes:
        path, cur = [], nid
        while cur is not None and cur not in top:
            par = parent_of.get(cur)
            if par == ROOT:
                top[cur] = cur
                break
            if par is None or par not in parent_of or len(path) > len(nodes):
                top[cur] = None
                break
            path.append(cur)
            cur = par
        t = top.get(cur) if cur is not None else None
        for p in path:
            top[p] = t
        if t is not None:
            counts[t] = counts.get(t, 0) + 1
    return counts


def init_text(head: str, nodes: dict) -> str:
    """Worker thread: the `init` frame around a partial document (head = the init frame without "doc")."""
    return f'{head[:-1]},"doc":{{"nodes":{dumps(nodes)}}}}}'


def page_text(pid: str, nodes: dict | None) -> str:
    """Worker thread: a `page` frame."""
    return dumps({"t": "page", "id": pid, "nodes": nodes})
