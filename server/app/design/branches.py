"""HOOLA DESIGN branches + merge (phase D9c, docs/HOOLA_DESIGN_PLAN.md section 8).

A BRANCH is a normal file (its own room, its own journal, edited like any file) linked to its MAIN file:
`design_files.branch_of` = main id, `branch_base_seq` = main's seq when the branch was made (or last updated from
main), `branch_state` "open" | "merged". The BASE document - main as it was at that seq - is kept with the branch
(`design_branches.base`, zlib JSON), because a merge is THREE-WAY:

    base   = main when the branch was made          ours   = the branch now          theirs = main now

per node and per property. A property changed on one side only takes that side's value; changed on both sides to
the same value is no conflict; changed on both sides to DIFFERENT values is a CONFLICT she decides ("ours" = the
branch's value, "theirs" = main's). The place of a node (`parent` + `idx`) counts as one property with two kinds of
conflict: MOVE (moved to different parents on both sides) and ORDER (re-ordered differently on both sides). The
structure conflicts: DELETED ON MAIN while it (or anything inside it) was changed here, and DELETED HERE while it
(or anything inside it) was changed on main - she keeps it or lets it go.

The merge is computed as a whole MERGED DOCUMENT, and the ops are the difference between the target (main for a
merge, the branch for "update from main") and that document - creates and moves ordered by depth so no step ever
makes a cycle, deletes last. The batch is checked against the document rules on a copy first (all or nothing), a
version of the target is saved first ("Before merging <branch>"), and the batch goes THROUGH the room
(HUB.apply_ops), so every editor open on main sees it land live. A merged branch is read only from then on.

Ids: every branch gets its own client-number range (branch n of a main starts at n * 1,000,000 + main's counter),
so a layer made on a branch can never share its id with one made on main or on another branch.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import undefer

from ..db import as_utc, now, session
from . import fracidx, store
from .doc import MAX_OP_BYTES, REJECTED, ROOT, Doc, dumps, loads
from .models import DesignBranch, DesignFile, ensure_tables

log = logging.getLogger("hoola.design.branches")

MAX_OPEN = 20                       # open branches of one main file
BASE_MAX = 32 * 1024 * 1024         # the stored base document, compressed
ID_RANGE = 1_000_000                # client numbers per branch
LIST_MAX = 2000                     # change rows in one preview (the counts are always whole)
PLACE = ("parent", "idx")
RELOAD = '{"t":"reload"}'


class BranchError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


# ============================================================================================ plain words
LABELS = {"x": "X", "y": "Y", "w": "Width", "h": "Height", "rot": "Rotation", "flipH": "Flip horizontal", "flipV": "Flip vertical",
          "fills": "Fill", "strokes": "Stroke", "strokeWeight": "Stroke weight", "strokeAlign": "Stroke position", "opacity": "Opacity",
          "visible": "Visible", "locked": "Locked", "name": "Name", "chars": "Text", "font": "Font", "fontSize": "Font size",
          "fontWeight": "Font weight", "italic": "Italic", "radius": "Corner radius", "effects": "Effects", "layout": "Auto layout",
          "blend": "Blend", "align": "Text align", "alignV": "Vertical align", "lineHeight": "Line height",
          "letterSpacing": "Letter spacing", "comp": "Component", "ov": "Overrides", "styles": "Styles", "vars": "Variables",
          "modes": "Modes", "bg": "Background", "reactions": "Prototype", "exports": "Export settings", "path": "Path",
          "type": "Type", "clip": "Clip content", "dash": "Dash", "grids": "Layout grids", "cons": "Constraints",
          "mask": "Mask", "bool": "Boolean", "sides": "Sides", "ratio": "Star ratio", "runs": "Text styles",
          "decoration": "Decoration", "textCase": "Letter case", "autoResize": "Resizing", "desc": "Description",
          "guides": "Guides", "sizeH": "Horizontal sizing", "sizeV": "Vertical sizing"}


def label(prop: str) -> str:
    if prop in LABELS:
        return LABELS[prop]
    words = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", str(prop)).strip()
    return (words[:1].upper() + words[1:].lower()) if words else str(prop)


def _num(v: float) -> str:
    r = round(float(v), 2)
    return str(int(r)) if r == int(r) else f"{r:g}"


def _paint(p: Any) -> str:
    if not isinstance(p, dict):
        return "custom"
    kind = p.get("type")
    hide = " (hidden)" if p.get("visible") is False else ""
    if kind == "solid":
        op = p.get("opacity", 1)
        tail = f" at {_num(float(op) * 100)}%" if isinstance(op, (int, float)) and op < 1 else ""
        return f"{str(p.get('color') or '#000000').upper()}{tail}{hide}"
    if kind in ("linear", "radial", "angular"):
        stops = [str(s.get("color", "")).upper() for s in p.get("stops") or [] if isinstance(s, dict)][:3]
        return f"{kind} gradient" + (f" {' to '.join(stops)}" if stops else "") + hide
    if kind == "image":
        return "an image" + hide
    return "custom" + hide


def say(value: Any) -> str:
    """A property value in plain words, for a conflict card."""
    if value is None:
        return "not set"
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, (int, float)):
        return _num(value)
    if isinstance(value, str):
        if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            return value.upper()
        text = " ".join(value.split())
        return f"“{text[:60]}{'…' if len(text) > 60 else ''}”"
    if isinstance(value, list):
        if not value:
            return "none"
        if all(isinstance(p, dict) and p.get("type") in ("solid", "linear", "radial", "angular", "image") for p in value):
            return ", ".join(_paint(p) for p in value[:3]) + (f" and {len(value) - 3} more" if len(value) > 3 else "")
        if all(isinstance(v, (int, float)) for v in value):
            return " / ".join(_num(v) for v in value[:8])
    raw = dumps(value)
    return raw if len(raw) <= 48 else raw[:47] + "…"


# ============================================================================================ the tree
def _kids(nodes: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for nid, n in nodes.items():
        p = n.get("parent")
        if isinstance(p, str):
            out.setdefault(p, []).append(nid)
    return out


def _subtree(kids: dict[str, list[str]], top: str) -> list[str]:
    out, stack = [], [top]
    while stack:
        cur = stack.pop()
        out.append(cur)
        stack.extend(kids.get(cur, ()))
    return out


def _top(nodes: dict, nid: str, inside: set[str]) -> str:
    """The highest ancestor of `nid` (itself included) that is still in `inside`, walking `nodes`' parents."""
    cur, steps = nid, len(nodes) + 1
    while steps > 0:
        p = nodes.get(cur, {}).get("parent")
        if not isinstance(p, str) or p not in inside:
            return cur
        cur, steps = p, steps - 1
    return cur


def _page(nodes: dict, nid: str) -> str | None:
    cur, steps = nid, 256
    while cur in nodes and steps > 0:
        if nodes[cur].get("type") == "PAGE":
            return cur
        cur, steps = nodes[cur].get("parent"), steps - 1
    return None


def _path(nodes: dict, nid: str) -> str:
    names, cur, steps = [], nid, 64
    while cur in nodes and cur != ROOT and steps > 0:
        n = nodes[cur]
        names.append(str(n.get("name") or n.get("type", "Layer").title()))
        cur, steps = n.get("parent"), steps - 1
    return " / ".join(reversed(names))


def _name(nodes: dict, nid: str) -> str:
    n = nodes.get(nid) or {}
    return str(n.get("name") or (n.get("type") or "Layer").title())


def _loc(docs: tuple, nid: str) -> dict:
    """Where a layer is, for the review list: from the first document of `docs` that has it."""
    src = next((d for d in docs if nid in d), {})
    pg = _page(src, nid)
    return {"node": nid, "name": _name(src, nid), "path": _path(src, nid), "type": (src.get(nid) or {}).get("type", ""),
            "page": pg, "page_name": _name(src, pg) if pg else ""}


def _props(*nodes: dict | None) -> list[str]:
    keys: set[str] = set()
    for n in nodes:
        if n:
            keys.update(n.keys())
    return sorted(k for k in keys if k not in PLACE)


# ============================================================================================ the analysis
def analyse(base: dict, ours: dict, theirs: dict) -> dict:
    """Base / ours (branch) / theirs (main) node dicts -> {changes, conflicts, counts, groups}. Pure."""
    B, O, T = base, ours, theirs
    okids, tkids = _kids(O), _kids(T)
    ours_touched = {i for i, n in O.items() if B.get(i) != n}
    theirs_touched = {i for i, n in T.items() if B.get(i) != n}
    conflicts: list[dict] = []
    gone_main: dict[str, list[str]] = {}            # top -> the branch's subtree under it (deleted on main)
    gone_here: dict[str, list[str]] = {}            # top -> main's subtree under it (deleted on the branch)

    def where(nid: str) -> dict:
        return _loc((O, T, B), nid)

    # ---- structure: deleted on one side, changed (inside) on the other
    deleted_main = {i for i in B if i in O and i not in T}
    tops = {_top(O, i, deleted_main) for i in deleted_main}
    for top in sorted(tops):
        sub = _subtree(okids, top)
        touched = [i for i in sub if i in ours_touched]
        if touched:
            gone_main[top] = sub
            conflicts.append({**where(top), "id": f"del-main:{top}", "kind": "deleted_main", "prop": None,
                              "ours": f"kept, {len(touched)} {'change' if len(touched) == 1 else 'changes'} inside",
                              "theirs": "deleted", "count": len(touched),
                              "text": f"Deleted on main, but changed here ({len(touched)} {'layer' if len(touched) == 1 else 'layers'})"})
    deleted_here = {i for i in B if i in T and i not in O}
    tops = {_top(T, i, deleted_here) for i in deleted_here}
    for top in sorted(tops):
        sub = _subtree(tkids, top)
        touched = [i for i in sub if i in theirs_touched]
        if touched:
            gone_here[top] = sub
            conflicts.append({**_loc((T, B), top), "id": f"del-here:{top}", "kind": "deleted_here", "prop": None, "ours": "deleted",
                              "theirs": f"kept, {len(touched)} {'change' if len(touched) == 1 else 'changes'} inside",
                              "count": len(touched),
                              "text": f"Deleted here, but changed on main ({len(touched)} {'layer' if len(touched) == 1 else 'layers'})"})

    # ---- the same node on both sides: property by property, and its place
    for i in sorted(set(O) & set(T)):
        o, t, b = O[i], T[i], B.get(i) or {}
        if o == t:
            continue
        for k in _props(b, o, t):
            bv, ov, tv = b.get(k), o.get(k), t.get(k)
            if ov != bv and tv != bv and ov != tv:
                conflicts.append({**where(i), "id": f"prop:{i}:{k}", "kind": "prop", "prop": k, "label": label(k),
                                  "ours": say(ov), "theirs": say(tv), "base": say(bv), "ours_value": ov, "theirs_value": tv,
                                  "text": f"{label(k)}: {say(ov)} here, {say(tv)} on main"})
        pb, po, pt = b.get("parent"), o.get("parent"), t.get("parent")
        ib, io, it = b.get("idx"), o.get("idx"), t.get("idx")
        both_moved = po != pb and pt != pb
        if both_moved and po != pt:
            conflicts.append({**where(i), "id": f"move:{i}", "kind": "move", "prop": "parent", "label": "Place",
                              "ours": f"inside {_name(O, po)}", "theirs": f"inside {_name(T, pt)}",
                              "text": f"Moved inside {_name(O, po)} here, inside {_name(T, pt)} on main"})
        elif po == pt and io != it and (both_moved or (io != ib and it != ib)):
            conflicts.append({**where(i), "id": f"order:{i}", "kind": "order", "prop": "idx", "label": "Order",
                              "ours": _order_words(O, okids, i), "theirs": _order_words(T, tkids, i),
                              "text": f"Order in {_name(T, pt)}: {_order_words(O, okids, i)} here, {_order_words(T, tkids, i)} on main"})

    in_conflict = {c["node"] for c in conflicts}
    changes = {"ours": _changes(B, O, okids, ours_touched, in_conflict),
               "theirs": _changes(B, T, tkids, theirs_touched, in_conflict)}
    counts = {side: {k: sum(1 for c in rows if c["kind"] == k) for k in ("added", "removed", "changed")}
              for side, rows in changes.items()}
    counts["conflicts"] = len(conflicts)
    for side in ("ours", "theirs"):
        counts[side]["total"] = len(changes[side])
        changes[side] = changes[side][:LIST_MAX]
    return {"changes": changes, "conflicts": conflicts, "counts": counts}


def _order_words(nodes: dict, kids: dict, nid: str) -> str:
    p = nodes.get(nid, {}).get("parent")
    sibs = sorted(kids.get(p, ()), key=lambda c: (nodes[c].get("idx", ""), c))
    if nid not in sibs:
        return "somewhere else"
    pos = len(sibs) - sibs.index(nid)          # the layers list shows the top-most first
    return f"layer {pos} of {len(sibs)} from the top"


def _changes(B: dict, S: dict, kids: dict, touched: set[str], in_conflict: set[str]) -> list[dict]:
    """One side's own changes against the base: added (top-most only), removed (top-most only), changed."""
    rows: list[dict] = []
    where = lambda nid: _loc((S, B), nid)                                                # noqa: E731
    added = {i for i in S if i not in B}
    for i in sorted(added):
        p = S[i].get("parent")
        if p in added:
            continue
        n_in = len(_subtree(kids, i))
        rows.append({**where(i), "id": f"add:{i}", "kind": "added", "props": [], "inside": n_in,
                     "conflict": i in in_conflict})
    removed = {i for i in B if i not in S}
    bkids = _kids(B)
    for i in sorted(removed):
        if B[i].get("parent") in removed:
            continue
        rows.append({**_loc((B,), i), "id": f"del:{i}", "kind": "removed", "props": [],
                     "inside": len(_subtree(bkids, i)), "conflict": i in in_conflict})
    for i in sorted(touched - added):
        b, s = B[i], S[i]
        props = [k for k in _props(b, s) if b.get(k) != s.get(k)]
        moved = b.get("parent") != s.get("parent")
        reordered = not moved and b.get("idx") != s.get("idx")
        words = [label(k) for k in props] + (["Moved"] if moved else []) + (["Order"] if reordered else [])
        if words:
            rows.append({**where(i), "id": f"chg:{i}", "kind": "changed", "props": words, "moved": moved,
                         "conflict": i in in_conflict})
    return rows


# ============================================================================================ the merged document
def build(base: dict, ours: dict, theirs: dict, resolutions: dict[str, str]) -> tuple[dict, list[str], list[dict]]:
    """The merged document as node dicts, the conflicts still unresolved (ids) and notes. Pure.
    Every conflict must be in `resolutions` as "ours" | "theirs" for the result to be used."""
    B, O, T = base, ours, theirs
    info = analyse(B, O, T)
    conflicts = {c["id"]: c for c in info["conflicts"]}
    open_ids = [cid for cid in conflicts if resolutions.get(cid) not in ("ours", "theirs")]
    pick = lambda cid: resolutions.get(cid, "theirs")                                   # noqa: E731
    okids = _kids(O)
    M: dict[str, dict] = {i: dict(n) for i, n in T.items()}
    from_ours: set[str] = set()
    notes: list[dict] = []

    # nodes kept by a "deleted on main" conflict resolved as ours come back whole (below); until then their
    # branch-made children are left out
    inside_gone_main: set[str] = set()
    for c in conflicts.values():
        if c["kind"] == "deleted_main":
            inside_gone_main.update(_subtree(okids, c["node"]))

    # 1. the same node on both sides
    for i in set(O) & set(T):
        o, t, m, b = O[i], T[i], M[i], B.get(i) or {}
        if o == t:
            continue
        for k in _props(b, o, t):
            bv, ov, tv = b.get(k), o.get(k), t.get(k)
            if ov == bv or ov == tv:
                continue
            if tv != bv and pick(f"prop:{i}:{k}") != "ours":
                continue
            if ov is None:
                m.pop(k, None)
            else:
                m[k] = ov
        pb, po, pt = b.get("parent"), o.get("parent"), t.get("parent")
        ib, io, it = b.get("idx"), o.get("idx"), t.get("idx")
        if (po, io) == (pt, it) or i == ROOT:
            continue
        use_ours = False
        if po != pb and pt != pb:
            use_ours = po == pt and pick(f"order:{i}") == "ours" if po == pt else pick(f"move:{i}") == "ours"
        elif po != pb:
            use_ours = True                                                             # moved here only
        elif pt != pb:
            use_ours = False                                                            # moved on main only
        elif io != ib and it != ib:
            use_ours = pick(f"order:{i}") == "ours"
        elif io != ib:
            use_ours = True
        if use_ours:
            m["parent"], m["idx"] = po, io
            from_ours.add(i)

    # 2. made on the branch only
    for i in set(O) - set(B) - set(T):
        if i in inside_gone_main:
            continue
        M[i] = dict(O[i])
        from_ours.add(i)

    # 3. deleted on the branch
    deleted_here = {i for i in B if i in T and i not in O}
    tkids = _kids(T)
    for top in {_top(T, i, deleted_here) for i in deleted_here}:
        cid = f"del-here:{top}"
        if cid in conflicts and pick(cid) != "ours":
            continue                                                                    # main's changes keep it
        for i in _subtree(tkids, top):
            if i not in O:
                M.pop(i, None)

    # 4. deleted on main, changed here: kept as the branch has it when she says so
    for c in conflicts.values():
        if c["kind"] != "deleted_main" or pick(c["id"]) != "ours":
            continue
        for i in _subtree(okids, c["node"]):
            if i not in M:
                M[i] = dict(O[i])
            else:
                M[i]["parent"], M[i]["idx"] = O[i].get("parent"), O[i].get("idx")
            from_ours.add(i)

    # 5. a node whose parent is not in the result: the other side's place, else it goes with its parent
    for _ in range(64):
        moved = False
        for i in list(M):
            if i == ROOT or i not in M:
                continue
            p = M[i].get("parent")
            if isinstance(p, str) and p in M:
                continue
            alt = T.get(i) if i in from_ours else O.get(i)
            if alt and alt.get("parent") in M:
                M[i]["parent"], M[i]["idx"] = alt.get("parent"), alt.get("idx")
                (from_ours.discard if i in from_ours else from_ours.add)(i)
            else:
                del M[i]
            moved = True
        if not moved:
            break

    # 6. a cycle (moved inside each other on the two sides): main's arrangement stays
    for i in list(M):
        loop = _cycle(M, i)
        if loop:
            for j in loop:
                if j in from_ours and j in T:
                    M[j]["parent"], M[j]["idx"] = T[j].get("parent"), T[j].get("idx")
                    from_ours.discard(j)
            notes.append({"node": i, "text": f"{_name(M, i)} stays where it is on main: the two moves would put "
                                              "layers inside each other."})

    # 7. siblings with the very same key: the branch's layer gets a fresh key right above it
    mkids = _kids(M)
    for p, kids in mkids.items():
        kids.sort(key=lambda c: (str(M[c].get("idx", "")), c))
        seen: dict[str, str] = {}
        for pos, c in enumerate(kids):
            key = str(M[c].get("idx", ""))
            if key in seen and c in from_ours:
                nxt = next((str(M[k].get("idx", "")) for k in kids[pos + 1:] if str(M[k].get("idx", "")) > key), None)
                M[c]["idx"] = fracidx.between(key, nxt)
            seen.setdefault(key, c)
    return M, open_ids, notes


def _cycle(M: dict, start: str) -> list[str]:
    seen, cur, chain = set(), start, []
    while isinstance(cur, str) and cur in M:
        if cur in seen:
            return chain[chain.index(cur):]
        seen.add(cur)
        chain.append(cur)
        cur = M[cur].get("parent")
    return []


def ops_between(target: dict, merged: dict) -> list[dict]:
    """The ops that turn `target` into `merged`: creates and moves shallow first (so no step makes a cycle and every
    parent exists before its child), the other property changes, then deletes (top-most only)."""
    depth: dict[str, int] = {}

    def d(nid: str) -> int:
        chain, cur = [], nid
        while cur in merged and cur not in depth and len(chain) < 10_000:
            chain.append(cur)
            cur = merged[cur].get("parent")
        base = depth.get(cur, -1) if isinstance(cur, str) else -1
        for j in reversed(chain):
            base += 1
            depth[j] = base
        return depth.get(nid, 0)

    early: list[tuple[int, str, dict]] = []
    late: list[dict] = []
    for i, m in merged.items():
        t = target.get(i)
        if t is None:
            early.append((d(i), i, {"id": i, "p": dict(m)}))
            continue
        if t == m:
            continue
        p = {k: m.get(k) for k in set(t) | set(m) if t.get(k) != m.get(k)}
        if "parent" in p or "idx" in p:
            p["parent"], p["idx"] = m.get("parent"), m.get("idx")
            if i == ROOT:
                p.pop("parent", None), p.pop("idx", None)
            early.append((d(i), i, {"id": i, "p": p}))
        else:
            late.append({"id": i, "p": p})
    early.sort(key=lambda e: (e[0], e[1]))
    gone = {i for i in target if i not in merged}
    dels = [{"id": i, "del": 1} for i in sorted(gone) if target[i].get("parent") not in gone]
    return [e[2] for e in early] + late + dels


def check_ops(target: dict, ops: list[dict], max_nodes: int) -> None:
    """Apply the batch to a copy of the target under the document rules: one refusal and nothing is applied."""
    doc = Doc({i: dict(n) for i, n in target.items()}, max_nodes)
    for op in ops:
        if len(dumps(op)) > MAX_OP_BYTES:
            raise BranchError(422, f"One change to {op['id']} is too large to send.")
        if doc.apply(op) == REJECTED:
            raise BranchError(422, f"The merge would break the file at layer {op['id']}; nothing was changed.")


def plan(base_json: str, ours_json: str, theirs_json: str, resolutions: dict, onto: str, max_nodes: int) -> dict:
    """Worker thread: the whole merge as {ops, notes, count} for `onto` = "theirs" (merge into main) or "ours"
    (update the branch from main). Raises BranchError 409 while a conflict is not decided."""
    B, O, T = (loads(j)["nodes"] for j in (base_json, ours_json, theirs_json))
    merged, open_ids, notes = build(B, O, T, resolutions)
    if open_ids:
        raise BranchError(409, f"{len(open_ids)} {'conflict is' if len(open_ids) == 1 else 'conflicts are'} not decided yet.")
    target = T if onto == "theirs" else O
    ops = ops_between(target, merged)
    check_ops(target, ops, max_nodes)
    return {"ops": ops, "notes": notes, "count": len(merged)}


def preview(base_json: str, ours_json: str, theirs_json: str) -> dict:
    B, O, T = (loads(j)["nodes"] for j in (base_json, ours_json, theirs_json))
    out = analyse(B, O, T)
    for c in out["conflicts"]:                     # the raw values stay on the server side of the card
        c.pop("ours_value", None)
        c.pop("theirs_value", None)
    return out


# ============================================================================================ rows
def _info(row: DesignFile, main: DesignFile | None = None) -> dict:
    return {"id": row.id, "name": row.name, "state": row.branch_state or "open", "main": row.branch_of,
            "main_name": main.name if main else "", "base_seq": row.branch_base_seq or 0,
            "trashed": row.trashed_at is not None,
            "updated_at": as_utc(row.updated_at).isoformat() if row.updated_at else None,
            "created_at": as_utc(row.created_at).isoformat() if row.created_at else None}


def _open_count(s, main_id: str) -> int:
    return int(s.scalar(select(func.count()).select_from(DesignFile).where(
        DesignFile.branch_of == main_id, DesignFile.trashed_at.is_(None),
        DesignFile.branch_state.is_distinct_from("merged"))) or 0)


def check_main(tenant: str, main_id: str) -> dict:
    """Worker thread: may a branch be made of this file?"""
    ensure_tables()
    with session() as s:
        row = s.get(DesignFile, main_id)
        if row is None or row.tenant_id != tenant or row.trashed_at is not None:
            raise BranchError(404, "File not found")
        if row.branch_of:
            raise BranchError(409, "This file is already a branch. Make the new branch from its main file.")
        if _open_count(s, main_id) >= MAX_OPEN:
            raise BranchError(409, f"A file can have {MAX_OPEN} open branches. Merge or delete one first.")
        return {"id": row.id, "name": row.name}


def insert_branch(tenant: str, main_id: str, name: str, doc_json: str, seq: int, node_count: int) -> dict:
    """Worker thread: the branch file + its base, in one transaction (the limits are checked again inside it)."""
    blob = store.pack(doc_json)
    if len(blob) > BASE_MAX:
        raise BranchError(413, "This file is too large to branch.")
    ensure_tables()
    with session() as s:
        main = s.get(DesignFile, main_id)
        if main is None or main.tenant_id != tenant or main.trashed_at is not None:
            raise BranchError(404, "File not found")
        if main.branch_of:
            raise BranchError(409, "This file is already a branch. Make the new branch from its main file.")
        if _open_count(s, main_id) >= MAX_OPEN:
            raise BranchError(409, f"A file can have {MAX_OPEN} open branches. Merge or delete one first.")
        no = int(s.scalar(select(func.max(DesignBranch.no)).where(DesignBranch.main_id == main_id)) or 0) + 1
        row = DesignFile(tenant_id=tenant, name=store.clean_name(name, store.clean_name(f"{main.name} branch")),
                         snapshot=blob, node_count=node_count, next_cid=no * ID_RANGE + max(1, main.next_cid),
                         branch_of=main_id, branch_base_seq=seq, branch_state="open")
        s.add(row)
        s.flush()
        s.add(DesignBranch(file_id=row.id, main_id=main_id, tenant_id=tenant, no=no, base=blob))
        s.flush()
        return _info(row, main)


def list_for(tenant: str, file_id: str) -> dict:
    """Worker thread: {file, is_branch, branch, main, branches} - the branches of the file's MAIN (itself, or the
    file it is a branch of), newest first."""
    ensure_tables()
    with session() as s:
        row = s.get(DesignFile, file_id)
        if row is None or row.tenant_id != tenant:
            raise BranchError(404, "File not found")
        main = s.get(DesignFile, row.branch_of) if row.branch_of else row
        if main is not None and main.tenant_id != tenant:
            main = None
        rows = []
        if main is not None:
            rows = s.scalars(select(DesignFile).where(DesignFile.branch_of == main.id, DesignFile.tenant_id == tenant,
                                                      DesignFile.trashed_at.is_(None))
                             .order_by(DesignFile.updated_at.desc(), DesignFile.id).limit(200)).all()
        return {"file": file_id, "is_branch": bool(row.branch_of),
                "branch": _info(row, main) if row.branch_of else None,
                "main": {"id": main.id, "name": main.name, "trashed": main.trashed_at is not None} if main else None,
                "branches": [_info(r, main) for r in rows], "max_open": MAX_OPEN}


def index(tenant: str) -> list[dict]:
    """Worker thread: every branch file of the tenant (for the badges in the file browser)."""
    ensure_tables()
    with session() as s:
        rows = s.execute(select(DesignFile.id, DesignFile.branch_of, DesignFile.branch_state)
                         .where(DesignFile.tenant_id == tenant, DesignFile.branch_of.is_not(None))).all()
        mains = {m.id: m.name for m in s.scalars(select(DesignFile).where(DesignFile.id.in_({r[1] for r in rows}))).all()} if rows else {}
        return [{"id": fid, "main": main, "main_name": mains.get(main, ""), "state": state or "open"} for fid, main, state in rows]


def branch_row(tenant: str, branch_id: str, want_base: bool = True) -> dict:
    """Worker thread: a branch with its main and (by default) its base document JSON."""
    ensure_tables()
    with session() as s:
        row = s.get(DesignFile, branch_id)
        if row is None or row.tenant_id != tenant or row.trashed_at is not None:
            raise BranchError(404, "File not found")
        if not row.branch_of:
            raise BranchError(409, "This file is not a branch.")
        main = s.get(DesignFile, row.branch_of)
        if main is None or main.tenant_id != tenant:
            raise BranchError(404, "The main file of this branch is gone.")
        out = {**_info(row, main), "main_trashed": main.trashed_at is not None}
        if want_base:
            b = s.get(DesignBranch, branch_id, options=[undefer(DesignBranch.base)])
            if b is None or not b.base:
                raise BranchError(409, "This branch has no base to compare against.")
            out["base_json"] = store.unpack(b.base)
        return out


def mark_merged(tenant: str, branch_id: str, by: str) -> None:
    with session() as s:
        row = s.get(DesignFile, branch_id)
        if row is None or row.tenant_id != tenant:
            return
        row.branch_state, row.updated_at = "merged", now()
        b = s.get(DesignBranch, branch_id)
        if b is not None:
            b.merged_at, b.merged_by = now(), by[:200]


def set_base(tenant: str, branch_id: str, doc_json: str, seq: int) -> None:
    blob = store.pack(doc_json)
    if len(blob) > BASE_MAX:
        raise BranchError(413, "The main file is too large to bring into this branch.")
    with session() as s:
        row = s.get(DesignFile, branch_id)
        b = s.get(DesignBranch, branch_id, options=[undefer(DesignBranch.base)])
        if row is None or row.tenant_id != tenant or b is None:
            return
        row.branch_base_seq = seq
        b.base = blob


def frozen(file_id: str) -> bool:
    """Worker thread: a merged branch is read only - its editors join as viewers."""
    ensure_tables()
    with session() as s:
        return s.scalar(select(DesignFile.branch_state).where(DesignFile.id == file_id)) == "merged"


# ============================================================================================ the service
def _settings_max() -> int:
    from ..config import get_settings
    return int(get_settings().design_max_nodes)


async def create(tenant: str, main_id: str, name: str) -> dict:
    from .room import HUB, bg
    await bg(check_main, tenant, main_id)
    got = await HUB.read(main_id, tenant)
    if got is None:
        raise BranchError(404, "File not found")
    seq, doc_json = got
    count = await bg(lambda: len(loads(doc_json)["nodes"]))
    return await bg(insert_branch, tenant, main_id, name, doc_json, seq, count)


async def compare(tenant: str, branch_id: str) -> dict:
    from .room import HUB, bg
    row = await bg(branch_row, tenant, branch_id)
    main = await HUB.read(row["main"], tenant)
    mine = await HUB.read(branch_id, tenant)
    if main is None or mine is None:
        raise BranchError(404, "File not found")
    out = await bg(preview, row.pop("base_json"), mine[1], main[1])
    return {**out, "branch": row, "main_seq": main[0], "branch_seq": mine[0], "base_seq": row["base_seq"]}


def _resolutions(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise BranchError(400, "resolutions is an object: {conflict id: \"ours\" | \"theirs\"}.")
    out = {}
    for k, v in value.items():
        if v not in ("ours", "theirs"):
            raise BranchError(400, f"Choose \"ours\" or \"theirs\" for {str(k)[:80]}.")
        out[str(k)] = v
    return out


async def apply(tenant: str, branch_id: str, body: dict, onto: str) -> dict:
    """onto "theirs" = merge the branch into main; "ours" = update the branch from main."""
    from .room import HUB, bg
    res = _resolutions(body.get("resolutions"))
    want_main, want_branch = body.get("main_seq"), body.get("branch_seq")
    if type(want_main) is not int:
        raise BranchError(400, "Send main_seq: the seq of main your review saw.")
    row = await bg(branch_row, tenant, branch_id)
    if row["state"] == "merged":
        raise BranchError(409, "This branch was merged already; it is read only now.")
    if row["main_trashed"]:
        raise BranchError(409, "The main file is in the trash. Restore it first.")
    base_json = row.pop("base_json")
    main_id = row["main"]
    target_id = main_id if onto == "theirs" else branch_id
    by = await bg(store.who, tenant)
    try:
        room = await HUB.open(target_id, tenant)
    except LookupError:
        raise BranchError(404, "File not found") from None
    try:
        saved = None
        for _ in range(4):
            main = await HUB.read(main_id, tenant)
            mine = await HUB.read(branch_id, tenant)
            if main is None or mine is None:
                raise BranchError(404, "File not found")
            if main[0] != want_main or (type(want_branch) is int and mine[0] != want_branch):
                raise BranchError(409, "The file changed since your review. Review it again.")
            got = await bg(plan, base_json, mine[1], main[1], res, onto, _settings_max())
            target_seq, target_json = main if onto == "theirs" else mine
            if saved is None:
                label = f"Before merging {row['name']}" if onto == "theirs" else "Before updating from main"
                count = await bg(lambda: len(loads(target_json)["nodes"]))
                saved = await bg(store.add_version, tenant, target_id, label, target_json, target_seq, count, by)
            # no await from here to the apply: the room is exactly the document the plan was made on
            if HUB.live(target_id) is not room or room.seq != target_seq:
                continue
            out = await HUB.apply_ops(target_id, tenant, got["ops"]) if got["ops"] else {"seq": room.seq, "rejected": []}
            break
        else:
            raise BranchError(409, "The file kept changing while merging. Try again.")
    finally:
        await HUB.release(room)
    if out.get("rejected"):
        log.error("design merge %s -> %s: %d ops refused after the check", branch_id, target_id, len(out["rejected"]))
    if onto == "theirs":
        await bg(mark_merged, tenant, branch_id, by)
        live = HUB.live(branch_id)
        if live is not None:                       # its editors become viewers: their next init says "view"
            for conn in list(live.conns.values()):
                conn.role = "view"
            live.tell(RELOAD)
    else:
        await bg(set_base, tenant, branch_id, main[1], main[0])
    return {"ok": True, "seq": out.get("seq"), "ops": len(got["ops"]), "rejected": out.get("rejected", []),
            "notes": got["notes"], "saved": saved, "target": target_id, "main": main_id, "branch": branch_id,
            "state": "merged" if onto == "theirs" else "open"}


# ============================================================================================ routes
class BranchIn(BaseModel):
    name: str | None = None


def mount(r, current_tenant) -> None:
    """The branch routes on the design router (key + switch already checked by the router)."""
    from .room import HUB, bg

    def fail(e: BranchError):
        raise HTTPException(e.status, str(e)) from None

    @r.get("/branches")
    async def branch_index(tenant: str = Depends(current_tenant)):
        return {"branches": await bg(index, tenant)}

    @r.get("/files/{file_id}/branches")
    async def branches(file_id: str, tenant: str = Depends(current_tenant)):
        try:
            return await bg(list_for, tenant, file_id)
        except BranchError as e:
            fail(e)

    @r.post("/files/{file_id}/branches")
    async def branch_new(file_id: str, body: BranchIn | None = None, tenant: str = Depends(current_tenant)):
        try:
            return await create(tenant, file_id, (body or BranchIn()).name or "")
        except BranchError as e:
            fail(e)

    @r.get("/files/{file_id}/merge")
    async def merge_preview(file_id: str, tenant: str = Depends(current_tenant)):
        try:
            return await compare(tenant, file_id)
        except BranchError as e:
            fail(e)

    @r.get("/files/{file_id}/merge/base")
    async def merge_base(file_id: str, tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response
        try:
            row = await bg(branch_row, tenant, file_id)
        except BranchError as e:
            fail(e)
        return Response(f'{{"seq":{row["base_seq"]},"doc":{row["base_json"]}}}', media_type="application/json")

    @r.post("/files/{file_id}/merge")
    async def merge_apply(file_id: str, body: dict, tenant: str = Depends(current_tenant)):
        try:
            return await apply(tenant, file_id, body or {}, "theirs")
        except BranchError as e:
            fail(e)

    @r.post("/files/{file_id}/update")
    async def update_apply(file_id: str, body: dict, tenant: str = Depends(current_tenant)):
        try:
            return await apply(tenant, file_id, body or {}, "ours")
        except BranchError as e:
            fail(e)

    _ = HUB                                           # imported for the reader: every write goes through it
