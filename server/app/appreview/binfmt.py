"""Static readers for app binaries. Pure Python, nothing here runs or loads the app:
- Android binary XML (APK AndroidManifest.xml / res/xml/*.xml) -> ElementTree
- aapt2 protobuf XML (AAB base/manifest/AndroidManifest.xml) -> ElementTree
- ELF program headers of native libraries (16 KB page-size check)
- class names and strings out of DEX / bundle bytes (SDK detection, secrets)
"""
from __future__ import annotations

import re
import struct
from typing import Any
from xml.etree import ElementTree as ET

ANDROID_NS = "http://schemas.android.com/apk/res/android"


class FormatError(Exception):
    pass


# ---------------------------------------------------------------- binary AXML
def _string_pool(b: bytes, off: int) -> list[str]:
    _t, hsz, _sz, count, _styles, flags, s_start, _st = struct.unpack_from("<HHIIIIII", b, off)
    utf8 = bool(flags & 0x100)
    offs = struct.unpack_from(f"<{count}I", b, off + hsz) if count else ()
    base = off + s_start
    out: list[str] = []
    for o in offs:
        p = base + o
        try:
            if utf8:
                n = b[p]
                p += 2 if n & 0x80 else 1
                ln = b[p]
                if ln & 0x80:
                    ln = ((ln & 0x7F) << 8) | b[p + 1]
                    p += 2
                else:
                    p += 1
                out.append(b[p:p + ln].decode("utf-8", "replace"))
            else:
                (ln,) = struct.unpack_from("<H", b, p)
                p += 2
                if ln & 0x8000:
                    (lo,) = struct.unpack_from("<H", b, p)
                    ln = ((ln & 0x7FFF) << 16) | lo
                    p += 2
                out.append(b[p:p + ln * 2].decode("utf-16le", "replace"))
        except (IndexError, struct.error):
            out.append("")
    return out


def _typed(dtype: int, data: int, pool: list[str]) -> str:
    if dtype == 0x03:
        return pool[data] if 0 <= data < len(pool) else ""
    if dtype == 0x12:
        return "true" if data else "false"
    if dtype == 0x10:
        return str(struct.unpack("<i", struct.pack("<I", data))[0])
    if dtype == 0x11:
        return f"0x{data:08x}"
    if dtype == 0x01:
        return f"@0x{data:08x}"
    if dtype == 0x02:
        return f"?0x{data:08x}"
    if dtype == 0x04:
        return repr(struct.unpack("<f", struct.pack("<I", data))[0])
    return str(data)


def parse_axml(b: bytes) -> ET.Element:
    """Binary Android XML -> ElementTree root. Attributes in the android namespace are '{ns}name' like a normal parse."""
    if len(b) < 8 or struct.unpack_from("<H", b, 0)[0] != 0x0003:
        raise FormatError("not binary xml")
    off = struct.unpack_from("<H", b, 2)[0]
    pool: list[str] = []
    stack: list[ET.Element] = []
    root: ET.Element | None = None
    while off + 8 <= len(b):
        ctype, hsz, csz = struct.unpack_from("<HHI", b, off)
        if csz < 8 or off + csz > len(b):
            break
        if ctype == 0x0001:
            pool = _string_pool(b, off)
        elif ctype == 0x0102:
            ns, name, a_start, a_size, a_count = struct.unpack_from("<IIHHH", b, off + 16)
            tag = pool[name] if name < len(pool) else "?"
            el = ET.Element(tag)
            ap = off + 16 + a_start
            for i in range(a_count):
                ans, aname, raw, _vs, _r, dtype, data = struct.unpack_from("<IIIHBBI", b, ap + i * (a_size or 20))
                key = pool[aname] if aname < len(pool) else ""
                uri = pool[ans] if ans != 0xFFFFFFFF and ans < len(pool) else ""
                val = pool[raw] if raw != 0xFFFFFFFF and raw < len(pool) else _typed(dtype, data, pool)
                el.set("{%s}%s" % (uri, key) if uri else key, val)
            if stack:
                stack[-1].append(el)
            else:
                root = el
            stack.append(el)
        elif ctype == 0x0103:
            if stack:
                stack.pop()
        off += csz
    if root is None:
        raise FormatError("empty binary xml")
    return root


# ---------------------------------------------------------------- protobuf XML (aapt2, inside .aab)
def _pb(b: bytes) -> dict[int, list[Any]]:
    out: dict[int, list[Any]] = {}
    i = 0
    n = len(b)

    def varint() -> int:
        nonlocal i
        shift = v = 0
        while True:
            if i >= n:
                raise FormatError("truncated varint")
            c = b[i]
            i += 1
            v |= (c & 0x7F) << shift
            if not c & 0x80:
                return v
            shift += 7
            if shift > 63:
                raise FormatError("bad varint")
    while i < n:
        key = varint()
        f, wt = key >> 3, key & 7
        if wt == 0:
            v: Any = varint()
        elif wt == 2:
            ln = varint()
            v = b[i:i + ln]
            i += ln
        elif wt == 5:
            v = b[i:i + 4]
            i += 4
        elif wt == 1:
            v = b[i:i + 8]
            i += 8
        else:
            raise FormatError("bad wire type")
        out.setdefault(f, []).append(v)
    return out


def _s(d: dict[int, list[Any]], f: int) -> str:
    v = d.get(f)
    return v[0].decode("utf-8", "replace") if v and isinstance(v[0], bytes) else ""


def _pb_attr_value(a: dict[int, list[Any]]) -> str:
    val = _s(a, 3)
    if val:
        return val
    item = a.get(6)
    if not item:
        return ""
    it = _pb(item[0])
    if 7 in it:                                   # Primitive
        p = _pb(it[7][0])
        if 8 in p:
            return "true" if p[8][0] else "false"
        for f in (6, 7):
            if f in p:
                v = p[f][0]
                return str(v - (1 << 64) if v >= 1 << 63 else v)
    if 2 in it:                                   # String
        return _s(_pb(it[2][0]), 1)
    if 1 in it:                                   # Reference
        r = _pb(it[1][0])
        return "@" + (_s(r, 3) or str((r.get(2) or [0])[0]))
    return ""


def _pb_element(node: bytes) -> ET.Element | None:
    d = _pb(node)
    if 1 not in d:
        return None
    e = _pb(d[1][0])
    el = ET.Element(_s(e, 3) or "?")
    for raw in e.get(4, []):
        a = _pb(raw)
        uri, name = _s(a, 1), _s(a, 2)
        el.set("{%s}%s" % (uri, name) if uri else name, _pb_attr_value(a))
    for ch in e.get(5, []):
        c = _pb_element(ch)
        if c is not None:
            el.append(c)
    return el


def parse_proto_xml(b: bytes) -> ET.Element:
    try:
        el = _pb_element(b)
    except (FormatError, IndexError) as e:
        raise FormatError(f"bad proto xml: {e}")
    if el is None:
        raise FormatError("empty proto xml")
    return el


def parse_any_xml(b: bytes) -> ET.Element:
    """Binary AXML, aapt2 protobuf or plain text XML."""
    if b[:2] == b"\x03\x00":
        return parse_axml(b)
    head = b.lstrip()[:5]
    if head.startswith(b"<"):
        try:
            return ET.fromstring(b)
        except ET.ParseError as e:
            raise FormatError(str(e))
    return parse_proto_xml(b)


def a(el: ET.Element, name: str, default: str = "") -> str:
    """android:<name> attribute (also accepts a missing namespace, as some tools write it)."""
    return el.get("{%s}%s" % (ANDROID_NS, name), el.get(name, default))


# ---------------------------------------------------------------- ELF
def elf_info(b: bytes) -> dict[str, Any]:
    """64/32-bit, machine, smallest PT_LOAD alignment (Play: 16 KB page size for 64-bit libs)."""
    if b[:4] != b"\x7fELF":
        return {"elf": False}
    cls, data = b[4], b[5]
    end = "<" if data == 1 else ">"
    try:
        (machine,) = struct.unpack_from(end + "H", b, 18)
        if cls == 2:
            (phoff,) = struct.unpack_from(end + "Q", b, 0x20)
            phentsize, phnum = struct.unpack_from(end + "HH", b, 0x36)
        else:
            (phoff,) = struct.unpack_from(end + "I", b, 0x1C)
            phentsize, phnum = struct.unpack_from(end + "HH", b, 0x2A)
        aligns = []
        for i in range(min(phnum, 64)):
            p = phoff + i * phentsize
            (ptype,) = struct.unpack_from(end + "I", b, p)
            if ptype != 1:
                continue
            if cls == 2:
                (al,) = struct.unpack_from(end + "Q", b, p + 48)
            else:
                (al,) = struct.unpack_from(end + "I", b, p + 28)
            aligns.append(al)
    except struct.error:
        return {"elf": True, "bits": 64 if cls == 2 else 32, "load_align": None}
    return {"elf": True, "bits": 64 if cls == 2 else 32, "machine": machine, "load_align": min(aligns) if aligns else None}


# ---------------------------------------------------------------- DEX / bundles
_CLASS = re.compile(rb"L([a-z][a-z0-9_]*(?:/[A-Za-z0-9_$]+){1,8});")


def class_prefixes(b: bytes, limit: int = 200_000) -> set[str]:
    """Dotted package names (first 2-4 parts) of every class descriptor in the DEX string table."""
    out: set[str] = set()
    for m in _CLASS.finditer(b):
        parts = m.group(1).decode("ascii", "ignore").split("/")[:-1]
        for k in range(2, min(len(parts), 4) + 1):
            out.add(".".join(parts[:k]))
        if len(out) > limit:
            break
    return out


_PRINT = re.compile(rb"[\x20-\x7e]{6,400}")


def printable_strings(b: bytes, limit: int = 400_000) -> list[str]:
    out = []
    for m in _PRINT.finditer(b):
        out.append(m.group(0).decode("ascii", "ignore"))
        if len(out) >= limit:
            break
    return out
