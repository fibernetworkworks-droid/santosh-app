"""draw.io XML for engine C (HOOLA DIAGRAM D3): read it, check it, change it cell by cell.

The rules are next-ai-draw-io's (vendor/drawio-ai/src/xml-validation.ts, diagram-operations.ts; Apache-2.0), written
here in Python for Hoola's server: one page (<mxfile><diagram><mxGraphModel><root>), the two root cells "0" and "1",
unique ids, every parent / source / target pointing at a real cell, no duplicated structural attribute; plus Hoola's
own safety line: a label or link may not carry a script (javascript:, <script, on...= handlers) - draw.io renders
labels as HTML, and an AI-written label is text, never code.

ops (what the model sends to change a diagram, id by id - never a rewrite of what she drew by hand):
  {"op": "update", "id": "b", "value": "API server", "style": "...", "x":..,"y":..,"width":..,"height":..}
  {"op": "add", "id": "c", "value": "Cache", "vertex": true, "x": 400, "y": 20, "width": 120, "height": 50, "style": "..."}
  {"op": "add", "id": "e2", "edge": true, "source": "b", "target": "c", "value": "reads"}
  {"op": "delete", "id": "c"}          (its edges go with it)"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re
import urllib.parse
import zlib
import xml.etree.ElementTree as ET
from typing import Any

MAX_CELLS = 2000
MAX_XML = 2_000_000
_BAD = re.compile(r"javascript\s*:|<\s*script\b|\bon[a-z]{3,20}\s*=|data\s*:\s*text/html", re.I)
_STRUCT = ("edge", "parent", "source", "target", "vertex", "connectable")


def _strip(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^```(?:xml)?\s*", "", t)
    return re.sub(r"\s*```$", "", t).strip()


def inflate(data: str) -> str | None:
    """A compressed draw.io page (what the editor itself saves): base64 -> raw deflate -> URI-encoded XML. Never more
    than MAX_XML comes out (a small page that unpacks to gigabytes is refused, not unpacked)."""
    try:
        raw = base64.b64decode("".join(str(data or "").split()), validate=True)
        d = zlib.decompressobj(-15)
        out = d.decompress(raw, MAX_XML + 1)
        if len(out) > MAX_XML or d.unconsumed_tail:
            return None
        return urllib.parse.unquote(out.decode("utf-8"))
    except (binascii.Error, zlib.error, UnicodeDecodeError, ValueError):
        return None


def parse(text: str) -> tuple[ET.Element | None, str]:
    """(the <root> element of the one page, problem). Accepts a whole <mxfile>, an <mxGraphModel>, a <root> or bare
    <mxCell> elements (the two root cells are added when missing)."""
    t = _strip(text)
    if not t:
        return None, "the diagram is empty"
    if len(t) > MAX_XML:
        return None, "the diagram is too large"
    if re.search(r"<!DOCTYPE|<!ENTITY", t, re.I):
        return None, "DOCTYPE / ENTITY declarations are not allowed"
    if not t.lstrip().startswith("<mxfile") and not t.lstrip().startswith("<mxGraphModel") \
            and not t.lstrip().startswith("<root"):
        t = "<root>" + t + "</root>"
    try:
        el = ET.fromstring(t)
    except ET.ParseError as e:
        return None, f"the XML does not parse ({e})"
    if el.tag == "mxfile":
        ds = el.findall("diagram")
        if len(ds) != 1:
            return None, "one page only (one <diagram> inside <mxfile>)"
        m = ds[0].find("mxGraphModel")
        if m is None and (ds[0].text or "").strip():
            plain = inflate(ds[0].text)
            if plain is None or re.search(r"<!DOCTYPE|<!ENTITY", plain, re.I):
                return None, "the page is compressed and could not be read - write it as plain XML"
            try:
                m = ET.fromstring(plain)
            except ET.ParseError as e:
                return None, f"the page does not parse ({e})"
            if m.tag != "mxGraphModel":
                m = None
        if m is None:
            return None, "the page has no <mxGraphModel> - write it as plain XML"
        el = m
    if el.tag == "mxGraphModel":
        el = el.find("root")
        if el is None:
            return None, "<mxGraphModel> has no <root>"
    if el.tag != "root":
        return None, f"unexpected <{el.tag}> - write <mxCell> elements"
    ids = [c.get("id") for c in el.findall("mxCell")]
    if "0" not in ids:
        el.insert(0, ET.Element("mxCell", {"id": "0"}))
    if "1" not in ids:
        el.insert(1, ET.Element("mxCell", {"id": "1", "parent": "0"}))
    return el, ""


def check(root: ET.Element) -> list[str]:
    probs: list[str] = []
    cells = list(root)
    if len(cells) > MAX_CELLS:
        probs.append(f"too many cells ({len(cells)}; at most {MAX_CELLS})")
    seen: set[str] = set()
    for c in cells:
        if c.tag not in ("mxCell", "UserObject", "object"):
            probs.append(f"<{c.tag}> is not a draw.io cell")
            continue
        cid = c.get("id") or ""
        if not cid:
            probs.append("a cell has no id")
        elif cid in seen:
            probs.append(f"id '{cid}' is used twice")
        seen.add(cid)
    for c in cells:
        cid = c.get("id") or "?"
        inner = c.find("mxCell") if c.tag in ("UserObject", "object") else c
        for k in ("parent", "source", "target"):
            v = (inner if inner is not None else c).get(k) or c.get(k)
            if v and v not in seen:
                probs.append(f"cell '{cid}': {k} '{v}' is not a cell")
        if c.get("id") not in ("0",) and not ((inner if inner is not None else c).get("parent") or c.get("parent")):
            probs.append(f"cell '{cid}' has no parent (use parent=\"1\")")
        for k, v in c.attrib.items():
            if _BAD.search(v or ""):
                probs.append(f"cell '{cid}': {k} carries a script - labels and links are text only")
        if (inner is not None and inner.get("edge") == "1") and not ((inner.get("source") or inner.get("target"))):
            g = inner.find("mxGeometry")
            if g is None or (g.find("mxPoint") is None and g.find("Array") is None):
                probs.append(f"edge '{cid}' has neither source/target nor points")
    return probs[:30]


def to_mxfile(root: ET.Element, name: str = "Page-1") -> str:
    model = ET.Element("mxGraphModel", {"grid": "1", "gridSize": "10", "guides": "1", "tooltips": "1",
                                        "connect": "1", "arrows": "1", "fold": "1", "page": "1", "pageScale": "1"})
    model.append(root)
    f = ET.Element("mxfile", {"host": "Hoola"})
    d = ET.SubElement(f, "diagram", {"id": "page-1", "name": name or "Page-1"})
    d.append(model)
    return ET.tostring(f, encoding="unicode")


def normalize(text: str, name: str = "Page-1") -> tuple[str, list[str]]:
    """(the clean one-page mxfile, problems) - problems empty = it may be drawn."""
    root, bad = parse(text)
    if root is None:
        return "", [bad]
    probs = check(root)
    return (to_mxfile(root, name) if not probs else ""), probs


def model_of(xml: str) -> str:
    """The <mxGraphModel> of the one page (what the editor's ReplaceDiagram takes)."""
    root, bad = parse(xml)
    if root is None:
        return ""
    m = ET.Element("mxGraphModel")
    m.append(root)
    return ET.tostring(m, encoding="unicode")


def fingerprint(xml: str) -> str:
    """What a person can change, nothing else: every cell's tag + sorted attributes + geometry (draw.io re-serialises
    with other attribute orders, whitespace and viewport attributes - none of that is an edit)."""
    root, _bad = parse(xml)
    if root is None:
        return ""
    h = hashlib.sha256()
    for c in root.iter():
        if c.tag in ("mxfile", "diagram", "mxGraphModel", "root"):
            continue
        h.update(c.tag.encode())
        for k in sorted(c.attrib):
            if k == "as" and c.tag == "mxGeometry":
                continue
            h.update(f"{k}={c.attrib[k]};".encode())
        h.update(b"|")
    return h.hexdigest()[:24]


def listing(xml: str, limit: int = 400) -> list[dict[str, Any]]:
    """The cells as the model reads them before a change: id, kind, label, parent, ends, geometry, style."""
    root, _bad = parse(xml)
    out: list[dict[str, Any]] = []
    if root is None:
        return out
    for c in list(root)[:limit]:
        cid = c.get("id")
        if cid in ("0", "1"):
            continue
        g = c.find("mxGeometry")
        row: dict[str, Any] = {"id": cid, "kind": "edge" if c.get("edge") == "1" else "shape",
                               "label": re.sub(r"<[^>]+>", " ", c.get("value") or "").strip()[:200]}
        for k in ("parent", "source", "target"):
            if c.get(k) and not (k == "parent" and c.get(k) == "1"):
                row[k] = c.get(k)
        if g is not None and c.get("edge") != "1":
            row["box"] = [g.get("x", "0"), g.get("y", "0"), g.get("width", ""), g.get("height", "")]
        if c.get("style"):
            row["style"] = c.get("style")[:160]
        out.append(row)
    return out


def _num(v: Any) -> str | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return str(int(f)) if f == int(f) else str(round(f, 2))


def apply_ops(xml: str, ops: list[dict[str, Any]]) -> tuple[str, list[str], list[str]]:
    """(new mxfile, changed ids, problems). All or nothing: one problem = nothing changes."""
    root, bad = parse(xml)
    if root is None:
        return "", [], [bad]
    if not isinstance(ops, list) or not ops:
        return "", [], ["ops must be a list of {op: update | add | delete, id, ...}"]
    by_id = {c.get("id"): c for c in root}
    changed: list[str] = []
    probs: list[str] = []
    for i, o in enumerate(ops[:200], 1):
        if not isinstance(o, dict):
            probs.append(f"op {i} is not an object")
            continue
        kind, cid = str(o.get("op") or "").lower(), str(o.get("id") or "")
        if not cid:
            probs.append(f"op {i}: id is required")
            continue
        if kind == "delete":
            if cid in ("0", "1") or cid not in by_id:
                probs.append(f"op {i}: no cell '{cid}' to delete")
                continue
            gone = {cid}
            for c in list(root):           # its children and the edges touching it go with it
                if c.get("parent") in gone or c.get("source") in gone or c.get("target") in gone:
                    gone.add(c.get("id"))
            for c in list(root):
                if c.get("id") in gone:
                    root.remove(c)
                    by_id.pop(c.get("id"), None)
            changed.append(cid)
            continue
        if kind == "add":
            if cid in by_id:
                probs.append(f"op {i}: id '{cid}' already exists - use update")
                continue
            edge = bool(o.get("edge"))
            c = ET.SubElement(root, "mxCell", {"id": cid, "value": str(o.get("value") or ""),
                                               "parent": str(o.get("parent") or "1")})
            c.set("edge" if edge else "vertex", "1")
            if o.get("style"):
                c.set("style", str(o["style"]))
            if edge:
                for k in ("source", "target"):
                    if o.get(k):
                        c.set(k, str(o[k]))
                ET.SubElement(c, "mxGeometry", {"relative": "1", "as": "geometry"})
            else:
                g = ET.SubElement(c, "mxGeometry", {"as": "geometry"})
                for k, d in (("x", 0), ("y", 0), ("width", 120), ("height", 60)):
                    g.set(k, _num(o.get(k, d)) or str(d))
            by_id[cid] = c
            changed.append(cid)
            continue
        if kind == "update":
            c = by_id.get(cid)
            if c is None or cid in ("0", "1"):
                probs.append(f"op {i}: no cell '{cid}' to update")
                continue
            if "value" in o:
                c.set("value", str(o.get("value") or ""))
            if "style" in o:
                c.set("style", str(o.get("style") or ""))
            for k in ("source", "target", "parent"):
                if k in o and o[k]:
                    c.set(k, str(o[k]))
            geo = {k: _num(o[k]) for k in ("x", "y", "width", "height") if k in o and _num(o[k]) is not None}
            if geo:
                g = c.find("mxGeometry")
                if g is None:
                    g = ET.SubElement(c, "mxGeometry", {"as": "geometry"})
                for k, v in geo.items():
                    g.set(k, v)
            changed.append(cid)
            continue
        probs.append(f"op {i}: op must be update, add or delete")
    if not probs:
        probs = check(root)
    if probs:
        return "", [], probs[:20]
    return to_mxfile(root), changed, []
