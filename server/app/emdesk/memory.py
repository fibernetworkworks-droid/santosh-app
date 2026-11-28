"""Where the flash and RAM go: a GNU ld map file (-Wl,-Map), `size -A` / `size` (Berkeley) output or `nm -S --size-sort` read
into the memory regions, the sections, the object files and the biggest symbols - with what fills a region, what the C library pulled
in (printf with floats, soft-float maths, malloc) and, given an older build, what grew. All read from the text she pastes."""
from __future__ import annotations

import re
from typing import Any


class MemError(ValueError):
    pass

FLASH_NAMES = (".isr_vector", ".vectors", ".text", ".rodata", ".ARM.extab", ".ARM.exidx", ".ARM", ".preinit_array", ".init_array",
               ".fini_array", ".init", ".fini", ".eh_frame", ".srodata", ".progmem", ".flash", ".gnu.sgstubs", ".vector_table")
RAM_NAMES = (".bss", ".sbss", ".noinit", "._user_heap_stack", ".heap", ".stack", ".tbss", ".ram", ".dma", ".ccmram", ".tdata")
NOT_LOADED = (".debug", ".comment", ".ARM.attributes", ".stab", ".note", ".riscv.attributes", ".gnu.attributes", ".symtab", ".strtab",
              ".shstrtab", "/DISCARD/", ".group")
LIBS = [  # (symbol or object pattern, what it means, typical cost)
    (r"_printf_float|_vfprintf_r|_svfprintf_r|_vfiprintf_r", "The printf family", "printf pulls in several KB; with -u _printf_float it adds the float formatter on top"),
    (r"_dtoa_r|__dtoa|_strtod_r", "float to text", "number formatting for floats (dtoa) - often from printf(\"%f\") or atof / strtod"),
    (r"__aeabi_d(?:mul|div|add|sub|cmp)|__adddf3|__muldf3|__divdf3|__subdf3|__extendsfdf2", "soft double maths",
     "double-precision maths in software - a float constant without an f suffix (1.5 instead of 1.5f) is enough to pull it in"),
    (r"__aeabi_f(?:mul|div|add|sub)|__addsf3|__mulsf3|__divsf3", "soft float maths", "single-precision maths in software (no FPU, or the FPU is not enabled in the build flags)"),
    (r"_malloc_r|\bmalloc\b|_free_r|_sbrk", "heap (malloc)", "dynamic memory - fragmentation and out-of-memory at run time on a small device"),
    (r"__cxa_throw|__gxx_personality|_Unwind_|__cxa_begin_catch", "C++ exceptions", "exception tables and unwinder - often tens of KB; -fno-exceptions removes them"),
    (r"std::|_ZNSt|_ZSt4cout|basic_ostream|ios_base", "C++ standard streams", "iostream and friends are large for a microcontroller"),
    (r"__cxa_guard_acquire|__cxa_atexit", "C++ static guards", "thread-safe static initialisation / atexit - -fno-threadsafe-statics drops the guards"),
    (r"\blog\b|\bexp\b|\bpow\b|\bsin\b|\bcos\b|\bsqrt\b|__ieee754", "libm", "maths library functions"),
]


def _int(s: str) -> int:
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def _parse_kb(v: Any) -> int:
    if v in (None, ""):
        return 0
    m = re.fullmatch(r"\s*([\d.]+)\s*([kKmM]?)(?:i?[bB])?\s*", str(v))
    if not m:
        raise MemError(f"A size like 256K, 64KB or 1M (got {v}).")
    n = float(m.group(1)) * {"": 1024, "k": 1024, "m": 1024 * 1024}[m.group(2).lower()]
    return int(n)


def _kind(name: str) -> str:
    n = name.lower()
    if any(n.startswith(x.lower()) for x in NOT_LOADED):
        return "none"
    if n.startswith(".data") or n.startswith(".sdata") or n == ".ramfunc" or n.startswith(".ramfunc"):
        return "data"
    if any(n.startswith(x.lower()) for x in RAM_NAMES):
        return "ram"
    if any(n.startswith(x.lower()) for x in FLASH_NAMES):
        return "flash"
    return "flash" if n.startswith(".text") else "?"


def _owner(path: str) -> str:
    path = path.strip()
    m = re.search(r"([^/\\]+\.a)\(([^)]+)\)$", path)
    if m:
        return f"{m.group(1)}({m.group(2)})"
    return re.split(r"[/\\]", path)[-1] or path


def _map(text: str) -> dict[str, Any]:
    regions, sections, inputs, syms = [], [], [], []
    lines = text.splitlines()
    i = 0
    m = re.search(r"Memory Configuration\s*\n\s*Name\s+Origin\s+Length[^\n]*\n((?:.*\n){0,40})", text)
    if m:
        for ln in m.group(1).splitlines():
            p = ln.split()
            if len(p) >= 3 and p[0] != "*default*" and re.fullmatch(r"0x[0-9a-fA-F]+", p[1]) and re.fullmatch(r"0x[0-9a-fA-F]+", p[2]):
                regions.append({"name": p[0], "origin": _int(p[1]), "length": _int(p[2]), "attr": p[3] if len(p) > 3 else ""})
            elif not ln.strip() and regions:
                break
    start = next((k for k, ln in enumerate(lines) if ln.startswith("Linker script and memory map")), 0)
    cur = None
    pending = None
    i = start
    while i < len(lines):
        ln = lines[i]
        i += 1
        mo = re.match(r"^(\.[\w.$@-]+|[A-Za-z_][\w.$]*)\s*$", ln)
        if mo and i < len(lines) and re.match(r"^\s+0x[0-9a-fA-F]+\s+0x[0-9a-fA-F]+", lines[i]):
            ln = mo.group(1) + " " + lines[i].strip()
            i += 1
        mo = re.match(r"^(\.[\w.$@-]+|/DISCARD/)\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)(?:\s+load address\s+(0x[0-9a-fA-F]+))?", ln)
        if mo:
            cur = {"name": mo.group(1), "addr": _int(mo.group(2)), "size": _int(mo.group(3)), "load": _int(mo.group(4)) if mo.group(4) else None,
                   "fill": 0}
            sections.append(cur)
            continue
        mi = re.match(r"^ (\.[\w.$@-]+|COMMON)\s*$", ln)
        if mi and i < len(lines):
            nx = re.match(r"^\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(\S.*)$", lines[i])
            if nx:
                ln = f" {mi.group(1)} {nx.group(1)} {nx.group(2)} {nx.group(3)}"
                i += 1
        mi = re.match(r"^ (\.[\w.$@-]+|COMMON)\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(\S.*)$", ln)
        if mi and cur is not None:
            size = _int(mi.group(3))
            if size:
                obj = mi.group(4).strip()
                inp = {"section": cur["name"], "input": mi.group(1), "addr": _int(mi.group(2)), "size": size, "obj": _owner(obj), "path": obj}
                inputs.append(inp)
                pending = inp
            else:
                pending = None
            continue
        mf = re.match(r"^ \*fill\*\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)", ln)
        if mf and cur is not None:
            cur["fill"] += _int(mf.group(2))
            continue
        ms = re.match(r"^\s{8,}(0x[0-9a-fA-F]+)\s{2,}([A-Za-z_$.][\w$.:<>~]*)\s*$", ln)
        if ms and pending is not None and _int(ms.group(1)) >= pending["addr"] and _int(ms.group(1)) < pending["addr"] + pending["size"]:
            syms.append({"name": ms.group(2), "addr": _int(ms.group(1)), "in": pending})
    if not sections:
        raise MemError("No output sections found in the map file (lines like '.text 0x08000000 0x5a3c').")
    # symbol sizes: the gap to the next symbol in the same input section
    by_inp: dict[int, list[dict[str, Any]]] = {}
    for s in syms:
        by_inp.setdefault(id(s["in"]), []).append(s)
    out_syms = []
    for lst in by_inp.values():
        lst.sort(key=lambda x: x["addr"])
        for k, s in enumerate(lst):
            end = lst[k + 1]["addr"] if k + 1 < len(lst) else s["in"]["addr"] + s["in"]["size"]
            out_syms.append({"name": s["name"], "size": max(0, end - s["addr"]), "addr": s["addr"], "section": s["in"]["section"], "obj": s["in"]["obj"]})
    for inp in inputs:
        mm = re.match(r"^\.(?:text|rodata|data|bss|sdata|sbss)\.(.+)$", inp["input"])
        if mm and not any(s["addr"] == inp["addr"] and s["section"] == inp["section"] for s in out_syms):
            out_syms.append({"name": mm.group(1), "size": inp["size"], "addr": inp["addr"], "section": inp["section"], "obj": inp["obj"]})
    return {"format": "map", "regions": regions, "sections": sections, "inputs": inputs, "symbols": out_syms}


def _size_a(text: str) -> dict[str, Any]:
    secs = []
    for ln in text.splitlines():
        m = re.match(r"^(\.[\w.$@-]+)\s+(\d+)\s*(\d+)?\s*$", ln.strip())
        if m:
            secs.append({"name": m.group(1), "size": int(m.group(2)), "addr": int(m.group(3)) if m.group(3) else 0, "load": None, "fill": 0})
    return {"format": "size -A", "regions": [], "sections": secs, "inputs": [], "symbols": []}


def _berkeley(text: str) -> dict[str, Any]:
    rows = []
    for ln in text.splitlines():
        m = re.match(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([0-9a-fA-F]+)\s*(.*)$", ln)
        if m:
            rows.append({"text": int(m.group(1)), "data": int(m.group(2)), "bss": int(m.group(3)), "file": m.group(6).strip()})
    if not rows:
        return {}
    r = rows[-1] if len(rows) == 1 or not rows[-1]["file"].lower().startswith("(tex") else rows[-1]
    tot = {"text": sum(x["text"] for x in rows), "data": sum(x["data"] for x in rows), "bss": sum(x["bss"] for x in rows)} if len(rows) > 1 else r
    secs = [{"name": ".text", "size": tot["text"], "addr": 0, "load": None, "fill": 0}, {"name": ".data", "size": tot["data"], "addr": 0, "load": None, "fill": 0},
            {"name": ".bss", "size": tot["bss"], "addr": 0, "load": None, "fill": 0}]
    inputs = [{"section": ".text", "input": ".text", "addr": 0, "size": x["text"] + x["data"], "obj": _owner(x["file"]) or "?", "path": x["file"]} for x in rows] if len(rows) > 1 else []
    return {"format": "size (Berkeley)", "regions": [], "sections": secs, "inputs": inputs, "symbols": [], "berkeley": True}


def _nm(text: str) -> dict[str, Any]:
    syms = []
    kinds = {"t": ".text", "w": ".text", "r": ".rodata", "d": ".data", "b": ".bss", "c": ".bss", "v": ".data", "g": ".data", "s": ".bss"}
    for ln in text.splitlines():
        m = re.match(r"^\s*([0-9a-fA-F]{4,16})\s+([0-9a-fA-F]{1,16})\s+([A-Za-z])\s+(\S.*)$", ln)
        if m and m.group(3).lower() in kinds:
            syms.append({"name": m.group(4).strip(), "size": int(m.group(2), 16), "addr": int(m.group(1), 16), "section": kinds[m.group(3).lower()], "obj": ""})
    if not syms:
        return {}
    by: dict[str, int] = {}
    for s in syms:
        by[s["section"]] = by.get(s["section"], 0) + s["size"]
    secs = [{"name": k, "size": v, "addr": 0, "load": None, "fill": 0} for k, v in by.items()]
    return {"format": "nm -S", "regions": [], "sections": secs, "inputs": [], "symbols": syms, "partial": True}


def parse(text: str) -> dict[str, Any]:
    text = str(text or "").replace("\r\n", "\n")
    if not text.strip():
        raise MemError("Paste a linker map file, `size -A` output, `size` output or `nm -S --size-sort` output.")
    if "Memory Configuration" in text or "Linker script and memory map" in text:
        return _map(text)
    if re.search(r"^section\s+size\s+addr", text, re.M) or re.search(r"^\.text\s+\d+\s+\d+\s*$", text, re.M):
        return _size_a(text)
    b = _berkeley(text) if re.search(r"text\s+data\s+bss", text) else {}
    if b:
        return b
    n = _nm(text)
    if n:
        return n
    raise MemError("Not a map file, `size` or `nm -S` output that this reads.")


def _sum(p: dict[str, Any]) -> dict[str, Any]:
    regs = [dict(r, used=0, parts={}) for r in p["regions"]]

    def region_of(addr: int) -> dict[str, Any] | None:
        for r in regs:
            if r["origin"] <= addr < r["origin"] + r["length"]:
                return r
        return None
    flash = ram = 0
    secs = []
    for s in p["sections"]:
        if s["size"] <= 0:
            continue
        k = _kind(s["name"])
        r_vma = region_of(s["addr"]) if regs and s["addr"] else None
        r_lma = region_of(s["load"]) if regs and s.get("load") else None
        if regs:
            if r_vma is None and r_lma is None:
                if k == "none" or s["addr"] == 0:
                    continue
            if r_vma is not None:
                r_vma["used"] += s["size"]
                r_vma["parts"][s["name"]] = r_vma["parts"].get(s["name"], 0) + s["size"]
            if r_lma is not None and r_lma is not r_vma:
                r_lma["used"] += s["size"]
                r_lma["parts"][s["name"] + " (copy)"] = s["size"]
            in_ram = r_vma is not None and ("w" in r_vma["attr"].lower() or re.search(r"ram|sram|data|ccm|dtcm", r_vma["name"], re.I))
            if in_ram:
                ram += s["size"]
                if r_lma is not None and r_lma is not r_vma:
                    flash += s["size"]
            elif r_vma is not None:
                flash += s["size"]
        else:
            if k == "none" or k == "?":
                if k == "?":
                    secs.append({"name": s["name"], "size": s["size"], "where": "?", "fill": s.get("fill", 0)})
                continue
            if k == "flash":
                flash += s["size"]
            elif k == "ram":
                ram += s["size"]
            else:
                flash += s["size"]
                ram += s["size"]
        where = "flash"
        if regs:
            rv = region_of(s["addr"]) if s["addr"] else None
            rl = region_of(s["load"]) if s.get("load") else None
            where = rv["name"] if rv else (rl["name"] if rl else "?")
            if rv and rl and rl is not rv:
                where = f"{rv['name']} (copy in {rl['name']})"
        else:
            where = {"flash": "flash", "ram": "RAM", "data": "flash + RAM"}[k]
        secs.append({"name": s["name"], "size": s["size"], "where": where, "fill": s.get("fill", 0)})
    return {"regions": regs, "flash": flash, "ram": ram, "sections": secs}


def analyse(text: str, flash: Any = "", ram: Any = "", before: str = "") -> dict[str, Any]:
    p = parse(text)
    s = _sum(p)
    fl_total, ram_total = _parse_kb(flash), _parse_kb(ram)
    regs = s["regions"]
    if not regs and (fl_total or ram_total):
        if fl_total:
            regs.append({"name": "FLASH", "origin": 0, "length": fl_total, "attr": "rx", "used": s["flash"], "parts": {}, "given": True})
        if ram_total:
            regs.append({"name": "RAM", "origin": 0, "length": ram_total, "attr": "rwx", "used": s["ram"], "parts": {}, "given": True})
    issues: list[dict[str, Any]] = []
    for r in regs:
        r["pct"] = round(100 * r["used"] / r["length"], 1) if r["length"] else None
        r["free"] = r["length"] - r["used"]
        r["parts"] = sorted(({"name": k, "size": v} for k, v in r["parts"].items()), key=lambda x: -x["size"])
        if r["pct"] is not None and r["pct"] > 100:
            issues.append({"sev": "bad", "text": f"{r['name']} is over full: {r['used']:,} of {r['length']:,} bytes ({r['pct']}%).", "area": "Size"})
        elif r["pct"] is not None and r["pct"] >= 90:
            issues.append({"sev": "warn", "text": f"{r['name']} is {r['pct']}% full - {r['free']:,} bytes left for the next features and for a bootloader or update slot.", "area": "Size"})
    by_obj: dict[str, dict[str, Any]] = {}
    for inp in p["inputs"]:
        k = _kind(inp["section"])
        if k == "none":
            continue
        o = by_obj.setdefault(inp["obj"], {"name": inp["obj"], "flash": 0, "ram": 0, "lib": ".a(" in inp["obj"] or inp["path"].endswith(".a")})
        if k in ("flash", "?"):
            o["flash"] += inp["size"]
        elif k == "ram":
            o["ram"] += inp["size"]
        else:
            o["flash"] += inp["size"]
            o["ram"] += inp["size"]
    objs = sorted(by_obj.values(), key=lambda x: -(x["flash"] + x["ram"]))
    syms = sorted((x for x in p["symbols"] if x["size"] > 0 and _kind(x["section"]) != "none"), key=lambda x: -x["size"])
    for sy in syms:
        sy["where"] = {"flash": "flash", "ram": "RAM", "data": "flash + RAM", "?": "flash"}[_kind(sy["section"])]
    names = " ".join(x["name"] for x in p["symbols"]) + " " + " ".join(x["input"] + " " + x["path"] for x in p["inputs"])
    pulled = []
    for pat, what, why in LIBS:
        hits = sorted({x["name"] for x in p["symbols"] if re.search(pat, x["name"])} | {x["obj"] for x in p["inputs"] if re.search(pat, x["input"] + " " + x["obj"])})
        if hits or (not p["symbols"] and re.search(pat, names)):
            cost = sum(x["size"] for x in p["symbols"] if re.search(pat, x["name"])) or sum(x["size"] for x in p["inputs"] if re.search(pat, x["input"] + " " + x["obj"]))
            pulled.append({"what": what, "why": why, "hits": hits[:6], "bytes": cost})
    for pl in pulled:
        sev = "warn" if pl["what"] in ("C++ exceptions", "heap (malloc)", "soft double maths", "C++ standard streams") else "info"
        issues.append({"sev": sev, "text": f"{pl['what'][0].upper() + pl['what'][1:]} is linked in" + (f" ({pl['bytes']:,} bytes)" if pl["bytes"] else "") + f": {pl['why']}.", "area": "Libraries",
                       "fix": ", ".join(pl["hits"][:4])})
    big_ram = [x for x in syms if x["where"] in ("RAM", "flash + RAM") and x["size"] >= 1024][:6]
    for x in big_ram[:3]:
        issues.append({"sev": "info", "text": f"{x['name']} takes {x['size']:,} bytes of RAM" + (f" ({x['obj']})" if x.get("obj") else "") + ".", "area": "RAM"})
    fill = sum(x.get("fill", 0) for x in s["sections"])
    if fill >= 256:
        issues.append({"sev": "info", "text": f"{fill:,} bytes are alignment padding (*fill*) between input sections.", "area": "Size"})
    heap = [x for x in s["sections"] if re.search(r"heap|stack", x["name"], re.I)]
    if heap:
        issues.append({"sev": "info", "text": "Reserved for heap and stack: " + ", ".join(f"{x['name']} {x['size']:,} bytes" for x in heap)
                       + " - counted as used RAM; whether that is enough only a stack measurement (-fstack-usage, a stack-paint check) tells.", "area": "RAM"})
    if p.get("partial"):
        issues.append({"sev": "info", "text": "nm lists symbols only: padding, the vector table's place and anything without a symbol are not counted.", "area": "Read"})
    grow = None
    if str(before or "").strip():
        try:
            pb = parse(before)
        except MemError as e:
            raise MemError("The older build: " + str(e))
        sb = _sum(pb)
        dsec: dict[str, int] = {}
        for x in sb["sections"]:
            dsec[x["name"]] = dsec.get(x["name"], 0) - x["size"]
        for x in s["sections"]:
            dsec[x["name"]] = dsec.get(x["name"], 0) + x["size"]
        osb: dict[str, int] = {}
        for inp in pb["inputs"]:
            if _kind(inp["section"]) != "none":
                osb[inp["obj"]] = osb.get(inp["obj"], 0) + inp["size"]
        dobj = {}
        for inp in p["inputs"]:
            if _kind(inp["section"]) != "none":
                dobj[inp["obj"]] = dobj.get(inp["obj"], 0) + inp["size"]
        for k2, v in osb.items():
            dobj[k2] = dobj.get(k2, 0) - v
        symb = {x["name"]: x["size"] for x in pb["symbols"]}
        syma = {x["name"]: x["size"] for x in p["symbols"]}
        dsym = {k2: syma.get(k2, 0) - symb.get(k2, 0) for k2 in set(symb) | set(syma)}
        grow = {"flash": s["flash"] - sb["flash"], "ram": s["ram"] - sb["ram"], "before": {"flash": sb["flash"], "ram": sb["ram"]},
                "sections": sorted(({"name": k2, "delta": v} for k2, v in dsec.items() if v), key=lambda x: -abs(x["delta"]))[:20],
                "objects": sorted(({"name": k2, "delta": v} for k2, v in dobj.items() if v), key=lambda x: -abs(x["delta"]))[:20],
                "symbols": sorted(({"name": k2, "delta": v, "new": k2 not in symb, "gone": k2 not in syma} for k2, v in dsym.items() if v), key=lambda x: -abs(x["delta"]))[:25]}
        if grow["flash"] > 0 or grow["ram"] > 0:
            issues.append({"sev": "info", "text": f"Since the older build: flash {grow['flash']:+,} bytes, RAM {grow['ram']:+,} bytes"
                           + (f" - most from {grow['objects'][0]['name']} ({grow['objects'][0]['delta']:+,})" if grow["objects"] else "") + ".", "area": "Growth"})
    counts = {k: sum(1 for i in issues if i["sev"] == k) for k in ("bad", "warn", "info")}
    head = ", ".join(f"{r['name']} {r['pct']}%" for r in regs if r["pct"] is not None) or f"flash {s['flash']:,} bytes, RAM {s['ram']:,} bytes"
    verdict = f"{head} - flash {s['flash']:,} bytes, RAM {s['ram']:,} bytes ({p['format']})."
    if not regs:
        verdict = f"Flash {s['flash']:,} bytes, RAM {s['ram']:,} bytes ({p['format']}) - set the chip's flash and RAM sizes to see how full they are."
    return {"format": p["format"], "flash": s["flash"], "ram": s["ram"], "regions": regs, "sections": sorted(s["sections"], key=lambda x: -x["size"]),
            "objects": objs[:60], "symbols": syms[:80], "libraries": pulled, "growth": grow, "issues": issues, "counts": counts, "verdict": verdict,
            "note": ("Read from the text pasted: a map file gives regions, objects and symbols; `size` gives sections only. Symbol sizes in a map file are the gap "
                     "to the next symbol, so the last symbol in an input section also carries its padding.")}
