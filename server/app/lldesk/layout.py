"""Struct layout worked out the way the compiler lays it out (C / C++ on the System V x86-64 and AArch64 ABIs - LP64 - or Windows
x64 - LLP64; Rust #[repr(C)] the same way): each field's offset and size, the padding, the cache lines each field sits on, fields that
cross a cache line, atomics that share a line (false sharing when different threads write them) and the order with the least padding.
Library types (std::string, std::vector, std::mutex) use libstdc++ / glibc sizes on 64-bit Linux, said as such."""
from __future__ import annotations

import re
from typing import Any


class LayoutError(ValueError):
    pass


def _base(abi: str) -> dict[str, tuple[int, int]]:
    lp = abi != "llp64"
    t = {"char": (1, 1), "signed char": (1, 1), "unsigned char": (1, 1), "bool": (1, 1), "_Bool": (1, 1), "short": (2, 2), "unsigned short": (2, 2),
         "int": (4, 4), "unsigned": (4, 4), "unsigned int": (4, 4), "long": (8, 8) if lp else (4, 4), "unsigned long": (8, 8) if lp else (4, 4),
         "long long": (8, 8), "unsigned long long": (8, 8), "float": (4, 4), "double": (8, 8), "long double": (16, 16) if lp else (8, 8),
         "size_t": (8, 8), "ssize_t": (8, 8), "ptrdiff_t": (8, 8), "intptr_t": (8, 8), "uintptr_t": (8, 8), "wchar_t": (4, 4) if lp else (2, 2),
         "char8_t": (1, 1), "char16_t": (2, 2), "char32_t": (4, 4), "__int128": (16, 16), "unsigned __int128": (16, 16),
         "std::byte": (1, 1), "std::size_t": (8, 8), "std::string": (32, 8), "std::string_view": (16, 8), "std::mutex": (40, 8),
         "std::atomic_flag": (1, 1), "std::condition_variable": (48, 8), "pthread_mutex_t": (40, 8), "pthread_spinlock_t": (4, 4),
         # Rust
         "u8": (1, 1), "i8": (1, 1), "u16": (2, 2), "i16": (2, 2), "u32": (4, 4), "i32": (4, 4), "u64": (8, 8), "i64": (8, 8),
         "u128": (16, 16), "i128": (16, 16), "usize": (8, 8), "isize": (8, 8), "f32": (4, 4), "f64": (8, 8), "char_rs": (4, 4),
         "AtomicBool": (1, 1), "AtomicU8": (1, 1), "AtomicI8": (1, 1), "AtomicU16": (2, 2), "AtomicI16": (2, 2), "AtomicU32": (4, 4),
         "AtomicI32": (4, 4), "AtomicU64": (8, 8), "AtomicI64": (8, 8), "AtomicUsize": (8, 8), "AtomicIsize": (8, 8)}
    for b in (8, 16, 32, 64):
        t[f"int{b}_t"] = t[f"uint{b}_t"] = t[f"std::int{b}_t"] = t[f"std::uint{b}_t"] = (b // 8, b // 8)
    return t


LIB = {"std::vector": (24, 8), "std::shared_ptr": (16, 8), "std::unique_ptr": (8, 8), "std::weak_ptr": (16, 8), "std::function": (32, 8),
       "std::optional": None, "std::array": None, "std::atomic": None, "std::pair": None, "std::unordered_map": (56, 8), "std::map": (48, 8),
       "std::deque": (80, 8), "Vec": (24, 8), "String": (24, 8), "Box": (8, 8), "Arc": (8, 8), "Rc": (8, 8), "Option": None,
       "AtomicPtr": (8, 8), "CachePadded": None}
ATOMIC = re.compile(r"^(?:std::atomic\b|Atomic[A-Z]|volatile\b|std::atomic_flag)")


def _clean(t: str) -> str:
    t = re.sub(r"//[^\n]*", "", t)
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return t


def _type(tp: str, known: dict[str, dict[str, Any]], base: dict[str, tuple[int, int]], lang: str) -> tuple[int, int, bool]:
    tp = re.sub(r"\b(?:const|mutable|struct|class|static)\b", " ", tp).strip()
    tp = re.sub(r"\s+", " ", tp)
    vol = tp.startswith("volatile ")
    tp = tp.replace("volatile ", "")
    if tp.endswith("*") or tp.endswith("&") or tp.startswith("*") or tp.startswith("&"):
        return 8, 8, vol
    if tp in base and not (lang == "rust" and tp == "char"):
        return base[tp][0], base[tp][1], vol or tp.startswith("Atomic")
    if lang == "rust" and tp == "char":
        return 4, 4, False
    m = re.fullmatch(r"\[(.+);\s*(\d+)\]", tp)
    if m:
        s, a, at = _type(m.group(1), known, base, lang)
        return s * int(m.group(2)), a, at
    m = re.fullmatch(r"([\w:]+)\s*<(.*)>", tp)
    if m:
        name, arg = m.group(1), m.group(2).strip()
        if name in ("std::atomic",):
            s, a, _ = _type(arg, known, base, lang)
            return s, max(a, s if s in (1, 2, 4, 8, 16) else a), True
        if name in ("std::optional", "Option"):
            if name == "Option" and re.match(r"(?:Box|Arc|Rc|&)", arg):
                return 8, 8, False
            s, a, _ = _type(arg, known, base, lang)
            return -(-(s + 1) // a) * a, a, False
        if name == "std::array":
            mm = re.fullmatch(r"(.+),\s*(\d+)", arg)
            if not mm:
                raise LayoutError(f"Cannot read '{tp}'.")
            s, a, at = _type(mm.group(1), known, base, lang)
            return s * int(mm.group(2)), a, at
        if name == "std::pair":
            x, y = [p.strip() for p in arg.split(",", 1)]
            s1, a1, _ = _type(x, known, base, lang)
            s2, a2, _ = _type(y, known, base, lang)
            al = max(a1, a2)
            off = -(-s1 // a2) * a2 + s2
            return -(-off // al) * al, al, False
        if name == "CachePadded":
            s, a, at = _type(arg, known, base, lang)
            return max(128, -(-s // 128) * 128), 128, at
        if LIB.get(name):
            return LIB[name][0], LIB[name][1], name == "AtomicPtr"
    if tp in LIB and LIB[tp]:
        return LIB[tp][0], LIB[tp][1], tp == "AtomicPtr"
    if tp in known:
        k = known[tp]
        return k["size"], k["align"], False   # a struct that holds atomics is not itself one atomic member
    if re.fullmatch(r"(?:enum\s+)?\w+", tp) and tp.endswith(("_e", "Kind", "Type", "State")):
        return 4, 4, False
    raise LayoutError(f"Unknown type '{tp}' - put its definition in the paste (before the struct that uses it).")


def _fields(body: str, lang: str) -> list[dict[str, Any]]:
    out = []
    if lang == "rust":
        for part in re.split(r",\s*(?![^<\[]*[>\]])", body):
            part = re.sub(r"#\[[^\]]*\]", "", part).strip()
            part = re.sub(r"^pub(?:\([^)]*\))?\s+", "", part)
            if not part:
                continue
            m = re.fullmatch(r"(\w+)\s*:\s*(.+)", part, re.S)
            if not m:
                raise LayoutError(f"Cannot read the field '{part[:60]}'.")
            out.append({"name": m.group(1), "type": m.group(2).strip(), "count": 1, "align_as": 0, "bits": 0})
        return out
    for stmt in body.split(";"):
        st = stmt.strip()
        if not st or st.startswith(("public:", "private:", "protected:")):
            st = re.sub(r"^(?:public|private|protected)\s*:\s*", "", st)
            if not st:
                continue
        if re.match(r"(?:static\b|using\b|typedef\b|friend\b|enum\b)", st) or "(" in st and not st.startswith("alignas"):
            continue
        al = 0
        m = re.match(r"alignas\s*\(\s*(\d+)\s*\)\s*(.*)$", st, re.S)
        if m:
            al, st = int(m.group(1)), m.group(2)
        st = re.sub(r"\s*=\s*[^,]+|\s*\{[^}]*\}", "", st)
        m = re.match(r"(.+?[\s*&>])((?:\w+\s*(?:\[\s*\d+\s*\])*\s*(?::\s*\d+)?\s*,\s*)*\w+\s*(?:\[\s*\d+\s*\])*\s*(?::\s*\d+)?)\s*$", st, re.S)
        if not m:
            raise LayoutError(f"Cannot read the field '{st[:60]}'.")
        tp = m.group(1).strip()
        for nm in m.group(2).split(","):
            nm = nm.strip()
            stars = ""
            while nm.startswith("*"):
                stars += "*"
                nm = nm[1:].strip()
            bits = 0
            bm = re.match(r"(\w+)\s*:\s*(\d+)$", nm)
            if bm:
                nm, bits = bm.group(1), int(bm.group(2))
            dims = [int(x) for x in re.findall(r"\[\s*(\d+)\s*\]", nm)]
            nm = re.sub(r"\[.*", "", nm).strip()
            cnt = 1
            for d in dims:
                cnt *= d
            out.append({"name": nm, "type": tp + stars, "count": cnt, "align_as": al, "bits": bits})
    return out


def _lay(fields: list[dict[str, Any]], known: dict[str, dict[str, Any]], base: dict[str, tuple[int, int]], lang: str, pack: int, salign: int, line: int) -> dict[str, Any]:
    off, mx, rows, pad = 0, 1, [], 0
    bit_unit = None   # (type size, byte offset, bits used)
    for f in fields:
        s, a, at = _type(f["type"], known, base, lang)
        if f["bits"]:
            if f["bits"] > s * 8:
                raise LayoutError(f"{f['name']}: {f['bits']} bits do not fit in {f['type']}.")
            a = min(a, pack) if pack else a
            if bit_unit and bit_unit[0] == s and bit_unit[2] + f["bits"] <= s * 8:
                bit_unit = (s, bit_unit[1], bit_unit[2] + f["bits"])
                rows[-1]["bits"] += f["bits"]
                rows[-1]["name"] += ", " + f["name"]
                continue
            start = -(-off // a) * a
            pad += start - off
            rows.append({"name": f["name"], "type": f["type"], "offset": start, "size": s, "align": a, "pad_before": start - off, "atomic": False, "bits": f["bits"]})
            bit_unit = (s, start, f["bits"])
            off = start + s
            mx = max(mx, a)
            continue
        bit_unit = None
        a = max(a, f["align_as"] or 1)
        if pack and not f["align_as"]:
            a = min(a, pack)
        size = s * f["count"]
        start = -(-off // a) * a
        rows.append({"name": f["name"], "type": f["type"] + (f"[{f['count']}]" if f["count"] > 1 else ""), "offset": start, "size": size, "align": a,
                     "pad_before": start - off, "atomic": at or bool(ATOMIC.match(f["type"].strip())), "bits": 0})
        pad += start - off
        off = start + size
        mx = max(mx, a)
    mx = max(mx, salign or 1)
    total = -(-off // mx) * mx if off else 0
    tail = total - off
    for r in rows:
        r["lines"] = [r["offset"] // line, (r["offset"] + max(r["size"], 1) - 1) // line]
        r["crosses"] = r["lines"][0] != r["lines"][1] and r["size"] <= line
    return {"rows": rows, "size": total, "align": mx, "padding": pad + tail, "tail": tail}


def analyse(text: str, abi: str = "lp64", line: int = 64) -> dict[str, Any]:
    t = _clean(str(text or ""))
    if len(t) > 400_000:
        raise LayoutError("That is longer than 400 KB.")
    abi = (abi or "lp64").lower()
    if abi not in ("lp64", "llp64"):
        raise LayoutError("ABI: lp64 (Linux / macOS, 64-bit) or llp64 (Windows x64).")
    line = int(line or 64)
    if line not in (32, 64, 128):
        raise LayoutError("Cache line: 32, 64 or 128 bytes.")
    base = _base(abi)
    known: dict[str, dict[str, Any]] = {}
    out = []
    pack_all = 1 if re.search(r"#pragma\s+pack\s*\(\s*(?:push\s*,\s*)?1\s*\)", t) else 0
    pat = re.compile(r"(#\[repr\(([^)]*)\)\]\s*)?(?:pub\s+)?(struct|class)\s+(?:alignas\s*\(\s*(\d+)\s*\)\s*)?(\w+)\s*(?:final\s*)?(?::\s*[^{]+)?\{", re.S)
    pos = 0
    while True:
        m = pat.search(t, pos)
        if not m:
            break
        depth, i = 1, m.end()
        while i < len(t) and depth:
            depth += {"{": 1, "}": -1}.get(t[i], 0)
            i += 1
        body = t[m.end():i - 1]
        tail = t[i:i + 60]
        pos = i
        name = m.group(5)
        lang = "rust" if (m.group(1) or re.search(r"\w+\s*:\s*[\w\[&]", body) and ";" not in body) else "c"
        if lang == "c" and re.search(r"\b(?:struct|class)\s+\w+\s*\{", body):
            body = re.sub(r"(?:struct|class)\s+\w+\s*\{[^{}]*\}\s*;", "", body)   # nested definitions are read separately
        repr_ = (m.group(2) or "").replace(" ", "")
        if lang == "rust" and "C" not in repr_.split(",") and "align" not in repr_:
            note = "no #[repr(C)]: Rust may reorder these fields; this is the declared order"
        else:
            note = ""
        packed = pack_all or (1 if "__attribute__((packed))" in tail.replace(" ", "") or "packed" in repr_ else 0)
        salign = int(m.group(4) or 0)
        ma = re.search(r"align\((\d+)\)", repr_)
        if ma:
            salign = int(ma.group(1))
        fields = _fields(body, lang)
        if not fields:
            continue
        L = _lay(fields, known, base, lang, packed, salign, line)
        best_order = sorted(fields, key=lambda f: (-(_type(f["type"], known, base, lang)[1]), -f["count"] * _type(f["type"], known, base, lang)[0]))
        B = _lay([f for f in best_order if not f["bits"]] + [f for f in fields if f["bits"]], known, base, lang, packed, salign, line)
        at_lines: dict[int, list[str]] = {}
        for r in L["rows"]:
            if r["atomic"]:
                for ln_ in range(r["lines"][0], r["lines"][1] + 1):
                    at_lines.setdefault(ln_, []).append(r["name"])
        issues = []
        for ln_, names in at_lines.items():
            if len(names) >= 2:
                issues.append({"sev": "warn", "text": f"{name}: {', '.join(names)} share cache line {ln_} - if different threads write them, the line moves between their cores on every write (false sharing).",
                               "fix": f"alignas({line}) on each one that another thread writes (or alignas(128) on Intel, where the prefetcher pulls pairs of lines; Rust: crossbeam's CachePadded)."})
        hot_other = [r["name"] for r in L["rows"] if not r["atomic"]]
        for ln_, names in at_lines.items():
            others = [r["name"] for r in L["rows"] if not r["atomic"] and r["lines"][0] <= ln_ <= r["lines"][1]]
            if names and others and len(names) == 1:
                issues.append({"sev": "info", "text": f"{name}: the atomic {names[0]} shares cache line {ln_} with {', '.join(others[:5])} - a write to it slows readers of those fields on other cores."})
        for r in L["rows"]:
            if r["crosses"]:
                issues.append({"sev": "info", "text": f"{name}.{r['name']} ({r['size']} bytes at offset {r['offset']}) crosses a cache-line boundary: reading it touches two lines" + (", and an atomic that crosses a line is very slow (a split lock)." if r["atomic"] else ".")})
        if B["size"] < L["size"]:
            issues.append({"sev": "info", "text": f"{name}: in the order below it takes {B['size']} bytes instead of {L['size']} ({L['size'] - B['size']} bytes of padding less)" +
                           (f" - {L['size'] // line + (1 if L['size'] % line else 0)} cache lines become {B['size'] // line + (1 if B['size'] % line else 0)}." if (L['size'] + line - 1) // line != (B['size'] + line - 1) // line else ".")})
        if note:
            issues.append({"sev": "info", "text": f"{name}: {note}."})
        if L["size"] > line and L["size"] % line and any(r["atomic"] for r in L["rows"]):
            issues.append({"sev": "info", "text": f"{name} is {L['size']} bytes: in an array, neighbouring elements share cache lines - pad it to a multiple of {line} if each element belongs to a different thread."})
        known[name] = {"size": L["size"], "align": L["align"], "has_atomic": any(r["atomic"] for r in L["rows"])}
        out.append({"name": name, "lang": "Rust" if lang == "rust" else "C / C++", "packed": bool(packed), **L,
                    "best": {"size": B["size"], "order": [r["name"] for r in B["rows"]]}, "issues": issues, "lines": (L["size"] + line - 1) // line})
    if not out:
        raise LayoutError("No struct found - paste a C / C++ struct or class, or a Rust struct.")
    issues = [i for s in out for i in s["issues"]]
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    return {"structs": out, "abi": abi, "line": line, "issues": issues, "counts": {k: sum(1 for i in issues if i["sev"] == k) for k in order},
            "verdict": ", ".join(f"{s['name']}: {s['size']} bytes ({s['padding']} padding, {s['lines']} cache line{'s' if s['lines'] != 1 else ''})" for s in out[:4]) + ".",
            "note": ("Laid out as the System V (Linux, macOS) or Windows x64 ABI does. std::string, std::vector, std::mutex and the like use libstdc++ / glibc "
                     "sizes on 64-bit Linux; MSVC and libc++ differ. Bit-fields are packed into units of their declared type, as GCC does.")}
