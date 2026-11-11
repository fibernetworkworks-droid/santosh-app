"""The in-memory document and the server's rules for every op (contract section 2).

`{"nodes": {id: {prop: value}}}`: a tree of nodes, each a flat bag of properties. The server is the authority:
it applies ops in arrival order, so the last writer of a property wins. `Doc.apply` either applies an op whole
or leaves the document untouched - a refused op never half-lands. A property value is always REPLACED, never
changed in place; `copy_nodes` relies on that to hand a consistent copy to another thread cheaply.
"""
from __future__ import annotations

import json
from typing import Any

from . import fracidx

ROOT = "0:0"
FIRST_PAGE = "0:1"
TYPES = frozenset("DOCUMENT PAGE FRAME GROUP SECTION RECT ELLIPSE LINE POLYGON STAR VECTOR TEXT "
                  "COMPONENT COMPONENT_SET INSTANCE".split())
MAX_NODES = 200_000
MAX_OP_BYTES = 256 * 1024
ID_MAX = 64
IDX_MAX = 256

APPLIED, DROPPED, REJECTED = 1, 0, -1     # DROPPED = accepted but a no-op (its node is already gone): not fanned out

# Starting frames for POST /files {template}. An unknown name is a blank file: a new template in the browser
# must never make "New file" fail.
TEMPLATES: dict[str, tuple[str, int, int]] = {
    "phone": ("Phone", 390, 844), "tablet": ("Tablet", 834, 1194), "desktop": ("Desktop", 1440, 1024),
    "social": ("Post", 1080, 1080), "presentation": ("Slide", 1920, 1080),
}


def _no_constant(name: str) -> Any:
    raise ValueError(f"{name} is not JSON")


def loads(text: str) -> Any:
    """json.loads that refuses NaN / Infinity: Python would echo them and every browser's JSON.parse would fail."""
    return json.loads(text, parse_constant=_no_constant)


def dumps(value: Any) -> str:
    """Compact JSON, ASCII only: a lone surrogate from one client must not break the UTF-8 frame of all the others."""
    return json.dumps(value, separators=(",", ":"))


def dumps_nodes(nodes: dict[str, dict]) -> str:
    return dumps({"nodes": nodes})


def _idx_ok(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= IDX_MAX and value.isascii()


class Doc:
    """One document in memory. Every method is O(size of its argument); none touches the whole tree
    except `copy_nodes` and the constructor."""

    __slots__ = ("nodes", "_kids", "max_nodes")

    def __init__(self, nodes: dict[str, dict], max_nodes: int = MAX_NODES):
        self.nodes = nodes
        self.max_nodes = max_nodes
        self._kids: dict[str, set[str]] = {}
        for nid, node in nodes.items():
            parent = node.get("parent")
            if isinstance(parent, str):
                self._kids.setdefault(parent, set()).add(nid)

    @classmethod
    def from_json(cls, text: str, max_nodes: int = MAX_NODES) -> "Doc":
        nodes = loads(text).get("nodes")
        if not isinstance(nodes, dict) or ROOT not in nodes:
            raise ValueError("not a design document")
        return cls(nodes, max_nodes)

    def __len__(self) -> int:
        return len(self.nodes)

    def children(self, parent: str) -> list[str]:
        """Child ids in drawing order: by `idx`, equal keys (two people inserted at one spot) by id."""
        nodes = self.nodes
        return sorted(self._kids.get(parent, ()), key=lambda c: (nodes[c].get("idx", ""), c))

    def copy_nodes(self) -> dict[str, dict]:
        """A copy another thread may serialise while ops keep landing here."""
        return {nid: node.copy() for nid, node in self.nodes.items()}

    # ------------------------------------------------------------------ ops
    def apply(self, op: Any) -> int:
        """Apply one op under the contract's rules. APPLIED / DROPPED / REJECTED; on REJECTED nothing changed."""
        if not isinstance(op, dict):
            return REJECTED
        nid = op.get("id")
        if not isinstance(nid, str) or not 0 < len(nid) <= ID_MAX:
            return REJECTED
        if op.get("del"):
            return self._delete(nid)
        props = op.get("p")
        if not isinstance(props, dict):
            return REJECTED
        node = self.nodes.get(nid)
        if node is None:
            return self._create(nid, props)
        return self._set(nid, node, props)

    def _create(self, nid: str, props: dict) -> int:
        kind = props.get("type")
        if kind is None:
            return DROPPED                    # a late edit of a node someone else deleted
        if not isinstance(kind, str) or kind not in TYPES or kind == "DOCUMENT":
            return REJECTED
        parent = props.get("parent")
        if not isinstance(parent, str) or parent not in self.nodes:
            return REJECTED
        if not _idx_ok(props.get("idx")) or len(self.nodes) >= self.max_nodes:
            return REJECTED
        self.nodes[nid] = {k: v for k, v in props.items() if v is not None}
        self._kids.setdefault(parent, set()).add(nid)
        return APPLIED

    def _set(self, nid: str, node: dict, props: dict) -> int:
        if "type" in props:
            kind = props["type"]
            if not isinstance(kind, str) or kind not in TYPES or (kind == "DOCUMENT") != (nid == ROOT):
                return REJECTED
        old_parent = node.get("parent")
        if "parent" in props:
            parent = props["parent"]
            if nid == ROOT or not isinstance(parent, str) or parent not in self.nodes:
                return REJECTED
            if parent != old_parent and self._inside(parent, nid):
                return REJECTED
        if "idx" in props and nid != ROOT and not _idx_ok(props["idx"]):
            return REJECTED
        for key, value in props.items():
            if value is None:
                node.pop(key, None)
            else:
                node[key] = value
        parent = node.get("parent")
        if parent != old_parent:
            kids = self._kids.get(old_parent)
            if kids:
                kids.discard(nid)
            self._kids.setdefault(parent, set()).add(nid)
        return APPLIED

    def _inside(self, start: str, ancestor: str) -> bool:
        """True when `ancestor` is `start` or above it: moving `ancestor` under `start` would close a cycle."""
        nodes, cur, steps = self.nodes, start, len(self.nodes)
        while cur is not None and steps >= 0:
            if cur == ancestor:
                return True
            node = nodes.get(cur)
            cur = node.get("parent") if node else None
            steps -= 1
        return steps < 0                      # a loop already in stored data: refuse to build on it

    def _delete(self, nid: str) -> int:
        if nid == ROOT:
            return REJECTED
        node = self.nodes.get(nid)
        if node is None:
            return DROPPED
        kids = self._kids.get(node.get("parent"))
        if kids:
            kids.discard(nid)
        stack = [nid]
        while stack:
            cur = stack.pop()
            self.nodes.pop(cur, None)
            below = self._kids.pop(cur, None)
            if below:
                stack.extend(below)
        return APPLIED


def new_document(template: str = "") -> dict[str, dict]:
    """A new file: the root, "Page 1" and - for a known template - one starting frame on it."""
    first = fracidx.between(None, None)
    nodes: dict[str, dict] = {
        ROOT: {"type": "DOCUMENT", "name": "Document"},
        FIRST_PAGE: {"type": "PAGE", "parent": ROOT, "idx": first, "name": "Page 1"},
    }
    frame = TEMPLATES.get((template or "").strip().lower())
    if frame:
        name, w, h = frame
        nodes["0:2"] = {"type": "FRAME", "parent": FIRST_PAGE, "idx": first, "name": name, "x": 0, "y": 0,
                        "w": w, "h": h, "fills": [{"type": "solid", "color": "#FFFFFF", "opacity": 1, "visible": True}]}
    return nodes
