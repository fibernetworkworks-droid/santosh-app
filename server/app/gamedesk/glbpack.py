"""v0.811 GAME TOOL HUB wave 1: one self-contained .glb from a glTF that points at outside files.

A game ships ONE file per model (`res://assets/<key>.glb`). Library models rarely arrive that way: Kenney's GLBs point
at a shared `Textures/colormap.png`, Poly Haven serves a .gltf + .bin + texture files. `embed` / `pack` put every
buffer and image INSIDE the GLB (as bufferViews), so nothing outside the file is ever needed - and nothing outside
the file can ever be reached: a uri that is not handed in by the caller is an error, never a fetch."""
from __future__ import annotations

import json
import struct
from typing import Callable

MAGIC = 0x46546C67
JSON_T, BIN_T = 0x4E4F534A, 0x004E4942
MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "ktx2": "image/ktx2"}


class PackError(Exception):
    pass


def split(glb: bytes) -> tuple[dict, bytes]:
    """(json, bin) of a GLB. Raises PackError on anything that is not a well-formed GLB 2."""
    if len(glb) < 20 or struct.unpack_from("<I", glb, 0)[0] != MAGIC or struct.unpack_from("<I", glb, 4)[0] != 2:
        raise PackError("not a GLB (glTF 2 binary) file")
    total = struct.unpack_from("<I", glb, 8)[0]
    if total > len(glb):
        raise PackError("the GLB is cut short")
    off, doc, blob = 12, None, b""
    while off + 8 <= total:
        n, kind = struct.unpack_from("<II", glb, off)
        body = glb[off + 8: off + 8 + n]
        if len(body) != n:
            raise PackError("the GLB is cut short")
        if kind == JSON_T and doc is None:
            try:
                doc = json.loads(body.decode("utf-8"))
            except ValueError:
                raise PackError("the GLB's JSON does not parse") from None
        elif kind == BIN_T and not blob:
            blob = bytes(body)
        off += 8 + n + (-n % 4)
    if not isinstance(doc, dict):
        raise PackError("the GLB has no JSON part")
    return doc, blob


def join(doc: dict, blob: bytes) -> bytes:
    js = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    js += b" " * (-len(js) % 4)
    blob = blob + b"\x00" * (-len(blob) % 4)
    out = struct.pack("<III", MAGIC, 2, 12 + 8 + len(js) + (8 + len(blob) if blob else 0))
    out += struct.pack("<II", len(js), JSON_T) + js
    if blob:
        out += struct.pack("<II", len(blob), BIN_T) + blob
    return out


def outside(doc: dict) -> list[str]:
    """Every uri the document still points at outside itself (data: uris are inside)."""
    out = []
    for part in ("buffers", "images"):
        for x in doc.get(part) or []:
            u = x.get("uri") if isinstance(x, dict) else None
            if isinstance(u, str) and u and not u.startswith("data:"):
                out.append(u)
    return out


def _pack(doc: dict, blob: bytes, files: Callable[[str], bytes | None]) -> bytes:
    doc = json.loads(json.dumps(doc))                   # our own copy
    buffers = doc.get("buffers") or []
    views = doc.setdefault("bufferViews", [])
    blob = bytearray(blob)
    blob += b"\x00" * (-len(blob) % 4)
    # every outside buffer goes behind the first one; its views move by that offset
    for i, b in enumerate(buffers):
        u = b.get("uri")
        if i == 0 and not u:
            continue
        if not isinstance(u, str) or u.startswith("data:"):
            raise PackError("a buffer inside a data: uri is not supported")
        data = files(u)
        if data is None:
            raise PackError(f"the model needs '{u[:80]}' and it was not given")
        shift = len(blob)
        blob += data
        blob += b"\x00" * (-len(blob) % 4)
        for v in views:
            if v.get("buffer") == i:
                v["buffer"] = 0
                v["byteOffset"] = int(v.get("byteOffset") or 0) + shift
    for im in doc.get("images") or []:
        u = im.get("uri")
        if not isinstance(u, str) or u.startswith("data:"):
            continue
        data = files(u)
        if data is None:
            raise PackError(f"the model needs the picture '{u[:80]}' and it was not given")
        ext = u.rsplit(".", 1)[-1].lower().split("?")[0]
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)})
        blob += data
        blob += b"\x00" * (-len(blob) % 4)
        im.pop("uri", None)
        im["bufferView"] = len(views) - 1
        im["mimeType"] = im.get("mimeType") or MIME.get(ext, "image/png")
    doc["buffers"] = [{"byteLength": len(blob)}] if blob else []
    left = outside(doc)
    if left:
        raise PackError("still points outside the file: " + ", ".join(left[:3]))
    return join(doc, bytes(blob))


def embed(glb: bytes, files: Callable[[str], bytes | None]) -> bytes:
    """A GLB whose images (or extra buffers) live in outside files -> one self-contained GLB."""
    doc, blob = split(glb)
    return glb if not outside(doc) else _pack(doc, blob, files)


def pack(gltf_json: bytes | str, files: Callable[[str], bytes | None]) -> bytes:
    """A .gltf document + its outside .bin / pictures (through `files`) -> one self-contained GLB."""
    try:
        doc = json.loads(gltf_json)
    except ValueError:
        raise PackError("the .gltf does not parse") from None
    if not isinstance(doc, dict) or "asset" not in doc:
        raise PackError("not a glTF document")
    return _pack(doc, b"", files)


def facts(glb: bytes) -> dict:
    """What is in a GLB, read from its own JSON: meshes, triangles (indexed primitives), materials, pictures, animations."""
    doc, _blob = split(glb)
    acc = doc.get("accessors") or []
    tris = 0
    for m in doc.get("meshes") or []:
        for p in m.get("primitives") or []:
            i = p.get("indices")
            if isinstance(i, int) and i < len(acc) and int(p.get("mode", 4)) == 4:
                tris += int(acc[i].get("count") or 0) // 3
    return {"meshes": len(doc.get("meshes") or []), "triangles": tris, "materials": len(doc.get("materials") or []),
            "images": len(doc.get("images") or []), "animations": len(doc.get("animations") or []),
            "outside": outside(doc), "bytes": len(glb)}
