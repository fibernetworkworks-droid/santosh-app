"""Lab Scene Language (LSL v1) checker. A lab is DATA only - bodies, knobs, instruments, a table, a tour - and this is
the gate every lab passes before a learner sees it (hand-written now, the AI author's in L7). Strict: an unknown key is
refused (so nothing like `script` / `html` / `onload` can ride in), every bind / instrument / column must point at
something real in the kernel, every number is finite and inside the stage, and the triangle count fits a phone."""
from __future__ import annotations

import math
import re
from typing import Any

from . import kernels as KN

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,60}$")
IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,40}$")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
NAMED = {"glass", "water", "steel", "brass", "copper", "wood", "red", "blue", "green", "black", "white", "gold", "ink", "ray",
         "glycerine", "mercury"}

TOP = {"lsl", "id", "title", "field", "group", "level", "topic", "aim", "kernel", "cfg", "params", "speed", "speeds",
       "autorun", "camera", "floor", "bodies", "knobs", "instruments", "table", "tour", "questions", "steps", "theory",
       "safety", "sources", "check", "lang"}
BODY_COMMON = {"id", "kind", "name", "info", "pos", "rot", "color", "opacity", "bind", "explode", "illustrative", "cut", "parent"}
KINDS: dict[str, set[str]] = {
    "box": {"size"}, "sphere": {"r"}, "cylinder": {"r", "r2", "h", "open"}, "cone": {"r", "h"},
    "torus": {"r", "tube", "arc"}, "plane": {"size"}, "dish": {"R", "r", "convex"}, "lens": {"r", "thick"},
    "prism": {"side", "depth", "angle"}, "spring": {"a", "b", "r", "turns", "wire"}, "rope": {"a", "b", "r", "bow"},
    "wire": {"pts", "r"}, "rays": {"var", "scale", "virtual"}, "arrow": {"dir", "len", "head"},
    "scale": {"length", "spacing", "major", "tick", "labels", "start", "label_step", "font", "down"},
    "text": {"text", "size"}, "needle": {"length", "w"}, "gas": {"size", "count", "r"},
}
TRIS = {"box": 12, "sphere": 1024, "cylinder": 256, "cone": 128, "torus": 1152, "plane": 2, "dish": 512, "lens": 1280,
        "prism": 8, "spring": 3500, "rope": 40, "wire": 40, "rays": 0, "arrow": 40, "scale": 0, "text": 2, "needle": 12,
        "gas": 96}
BIND_KEYS = {"x", "y", "z", "rx", "ry", "rz", "sx", "sy", "sz", "len", "visible", "opacity", "mark", "h"}
KNOB_KEYS = {"id", "label", "param", "min", "max", "step", "value", "unit", "k", "reset", "digits", "hidden", "hint"}
INST_KINDS = {"readout", "stopwatch", "graph", "meter"}
INST_KEYS = {"id", "kind", "label", "var", "unit", "k", "lc", "digits", "x", "xk", "xlabel", "range", "peak", "hint", "dots"}
COL_KEYS = {"id", "label", "from", "unit", "k", "div", "digits"}
TABLE_KEYS = {"columns", "calc", "rows_min", "truth", "result_k", "result_unit", "result_digits", "hint"}
TOUR_KEYS = {"cam", "look", "say", "set", "run"}
Q_KEYS = {"q", "options", "answer", "why"}
CHECK_KEYS = {"params", "reading", "textbook", "tol", "measure", "rows", "calc"}
ROW_KEYS = {"set", "measure", "take", "add"}
STAGE = 50.0
MAX_TRIS = 80000


class LabError(ValueError):
    pass


def _num(v: Any, where: str, lo: float = -STAGE, hi: float = STAGE) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise LabError(f"{where}: needs a number")
    if not lo <= v <= hi:
        raise LabError(f"{where}: {v} is out of range ({lo}..{hi})")
    return float(v)


def _vec(v: Any, where: str, n: int = 3) -> None:
    if not isinstance(v, list) or len(v) != n:
        raise LabError(f"{where}: needs a list of {n} numbers")
    for i, x in enumerate(v):
        _num(x, f"{where}[{i}]")


def _text(v: Any, where: str, mx: int = 400, need: bool = False) -> None:
    if v is None and not need:
        return
    if not isinstance(v, str) or (need and not v.strip()) or len(v) > mx:
        raise LabError(f"{where}: needs text (<= {mx} characters)")


def _keys(d: Any, allowed: set[str], where: str) -> dict:
    if not isinstance(d, dict):
        raise LabError(f"{where}: needs an object")
    extra = set(d) - allowed
    if extra:
        raise LabError(f"{where}: unknown key {sorted(extra)} - a lab is data only")
    return d


def _ref_ok(name: str, kvars: set[str], params: set[str], knobs: set[str]) -> bool:
    if name.startswith("p."):
        return name[2:] in params
    if name.startswith("knob:"):
        return name[5:] in knobs
    return name in kvars


def _bind_spec(spec: Any, where: str, kvars, params, knobs) -> None:
    if isinstance(spec, str):
        name = spec
    else:
        _keys(spec, {"var", "k", "c", "min", "max"}, where)
        name = spec.get("var")
        for k in ("k", "c", "min", "max"):
            if k in spec:
                _num(spec[k], f"{where}.{k}", -1e9, 1e9)
    if not isinstance(name, str) or not _ref_ok(name, kvars, params, knobs):
        raise LabError(f"{where}: '{name}' is not a kernel var / param / knob")


def _color(v: Any, where: str) -> None:
    if v is None:
        return
    if not isinstance(v, str) or not (COLOR.match(v) or v in NAMED):
        raise LabError(f"{where}: colour must be #rrggbb or one of {sorted(NAMED)}")


def _net(cfg: dict) -> None:
    net = _keys(cfg.get("net"), {"nodes", "els"}, "cfg.net")
    nn = int(_num(net.get("nodes"), "cfg.net.nodes", 1, 40))
    els = net.get("els")
    if not isinstance(els, list) or not 1 <= len(els) <= 80:
        raise LabError("cfg.net.els: needs 1-80 parts")
    ids = set()
    for i, e in enumerate(els):
        w = f"cfg.net.els[{i}]"
        _keys(e, {"id", "kind", "a", "b", "value", "param", "Is", "n"}, w)
        if not isinstance(e.get("id"), str) or not IDENT.match(e["id"]) or e["id"] in ids:
            raise LabError(f"{w}.id: needs a unique name")
        ids.add(e["id"])
        if e.get("kind") not in {"R", "V", "C", "D", "S"}:
            raise LabError(f"{w}.kind: R / V / C / D / S")
        for t in ("a", "b"):
            v = e.get(t)
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= nn:
                raise LabError(f"{w}.{t}: node 0..{nn}")
        if e["a"] == e["b"]:
            raise LabError(f"{w}: both ends on the same node")
        if e["kind"] == "S":
            if not isinstance(e.get("param"), str):
                raise LabError(f"{w}: a switch needs a param")
        elif e["kind"] != "D" and "value" not in e:
            raise LabError(f"{w}: needs a value")


def check(lab: dict) -> dict:
    """Validate a lab; return it unchanged or raise LabError naming the first problem."""
    _keys(lab, TOP, "lab")
    if lab.get("lsl") != 1:
        raise LabError("lab.lsl: 1")
    if not isinstance(lab.get("id"), str) or not SLUG.match(lab["id"]):
        raise LabError("lab.id: a short slug (a-z, 0-9, -)")
    for k, mx in (("title", 80), ("field", 40), ("group", 60), ("level", 60), ("topic", 120), ("aim", 300),
                  ("theory", 1500), ("safety", 600), ("lang", 10)):
        _text(lab.get(k), f"lab.{k}", mx, need=k in ("title", "field", "aim"))
    name = lab.get("kernel")
    if name not in KN.KERNELS:
        raise LabError(f"lab.kernel: unknown kernel '{name}'")
    cfg = lab.get("cfg") or {}
    _keys(cfg, {"net", "measure"}, "lab.cfg")
    if name == "circuit":
        _net(cfg)
    elif "net" in cfg:
        raise LabError("lab.cfg.net is only for the circuit kernel")
    params = set(KN.params_for(name, {}).keys())
    over = _keys(lab.get("params") or {}, set(lab.get("params") or {}), "lab.params")
    for k, v in over.items():
        if not IDENT.match(k):
            raise LabError(f"lab.params.{k}: bad name")
        _num(v, f"lab.params.{k}", -1e12, 1e12)
    params |= set(over)
    if name != "circuit" and set(over) - set(KN.KERNELS[name].PARAMS):
        raise LabError(f"lab.params: {sorted(set(over) - set(KN.KERNELS[name].PARAMS))} not in kernel '{name}'")
    kvars = set(KN.kernel_vars(name, cfg))
    for k in ("speed",):
        if k in lab:
            _num(lab[k], f"lab.{k}", 0.01, 1000)
    if "speeds" in lab:
        if not isinstance(lab["speeds"], list) or len(lab["speeds"]) > 8:
            raise LabError("lab.speeds: <= 8 numbers")
        for i, s in enumerate(lab["speeds"]):
            _num(s, f"lab.speeds[{i}]", 0.01, 1000)
    cam = _keys(lab.get("camera") or {}, {"pos", "look"}, "lab.camera")
    for k in ("pos", "look"):
        if k in cam:
            _vec(cam[k], f"lab.camera.{k}")
    if "floor" in lab:
        _num(lab["floor"], "lab.floor")

    knobs = lab.get("knobs") or []
    if not isinstance(knobs, list) or len(knobs) > 10:
        raise LabError("lab.knobs: <= 10")
    kids: set[str] = set()
    for i, k in enumerate(knobs):
        w = f"knobs[{i}]"
        _keys(k, KNOB_KEYS, w)
        if not isinstance(k.get("id"), str) or not IDENT.match(k["id"]) or k["id"] in kids:
            raise LabError(f"{w}.id: needs a unique name")
        kids.add(k["id"])
        _text(k.get("label"), f"{w}.label", 80, need=True)
        if k.get("param") not in params:
            raise LabError(f"{w}.param: '{k.get('param')}' is not a kernel param")
        lo, hi = _num(k.get("min"), f"{w}.min", -1e9, 1e9), _num(k.get("max"), f"{w}.max", -1e9, 1e9)
        st = _num(k.get("step"), f"{w}.step", 1e-12, 1e9)
        val = _num(k.get("value"), f"{w}.value", -1e9, 1e9)
        if not lo < hi or not lo <= val <= hi or st > hi - lo:
            raise LabError(f"{w}: needs min < max, value between them, a small step")
        if "k" in k:
            _num(k["k"], f"{w}.k", -1e9, 1e9)
        for t in ("unit", "hint"):
            _text(k.get(t), f"{w}.{t}", 120)

    insts = lab.get("instruments") or []
    if not isinstance(insts, list) or len(insts) > 10:
        raise LabError("lab.instruments: <= 10")
    iids: set[str] = set()
    for i, m in enumerate(insts):
        w = f"instruments[{i}]"
        _keys(m, INST_KEYS, w)
        if m.get("kind") not in INST_KINDS:
            raise LabError(f"{w}.kind: {sorted(INST_KINDS)}")
        if not isinstance(m.get("id"), str) or not IDENT.match(m["id"]) or m["id"] in iids:
            raise LabError(f"{w}.id: needs a unique name")
        iids.add(m["id"])
        _text(m.get("label"), f"{w}.label", 80, need=True)
        if m["kind"] != "stopwatch":
            v = m.get("var")
            if not isinstance(v, str) or not _ref_ok(v, kvars, params, kids):
                raise LabError(f"{w}.var: '{v}' is not in the kernel")
        if "x" in m and not (isinstance(m["x"], str) and _ref_ok(m["x"], kvars, params, kids)):
            raise LabError(f"{w}.x: '{m.get('x')}' is not in the kernel")
        for t in ("k", "lc", "xk"):
            if t in m:
                _num(m[t], f"{w}.{t}", -1e12, 1e12)
        if "range" in m:
            if not isinstance(m["range"], list) or len(m["range"]) != 2:
                raise LabError(f"{w}.range: [lo, hi]")
            for j, x in enumerate(m["range"]):
                _num(x, f"{w}.range[{j}]", -1e12, 1e12)

    bodies = lab.get("bodies") or []
    if not isinstance(bodies, list) or not 1 <= len(bodies) <= 150:
        raise LabError("lab.bodies: 1-150")
    bids: set[str] = set()
    tris = 0
    for i, b in enumerate(bodies):
        w = f"bodies[{i}]"
        kind = b.get("kind") if isinstance(b, dict) else None
        if kind not in KINDS:
            raise LabError(f"{w}.kind: {sorted(KINDS)}")
        _keys(b, BODY_COMMON | KINDS[kind], w)
        if not isinstance(b.get("id"), str) or not IDENT.match(b["id"]) or b["id"] in bids:
            raise LabError(f"{w}.id: needs a unique name")
        _text(b.get("name"), f"{w}.name", 80)
        _text(b.get("info"), f"{w}.info", 300)
        _text(b.get("text"), f"{w}.text", 60)
        _color(b.get("color"), f"{w}.color")
        if "parent" in b and b["parent"] not in bids:
            raise LabError(f"{w}.parent: must be a body listed earlier")
        if kind in ("spring", "rope") and "parent" in b:
            raise LabError(f"{w}: a spring / rope has no parent (its ends are in world space)")
        for k in ("pos", "rot", "explode", "dir"):
            if k in b:
                _vec(b[k], f"{w}.{k}")
        if kind == "text" and "size" in b:
            _num(b["size"], f"{w}.size", 0.001, 5)
        for k in ("size",):
            if k in b and kind != "text":
                _vec(b[k], f"{w}.{k}", 3 if kind in ("box", "gas") else 2)
                for j, x in enumerate(b[k]):
                    _num(x, f"{w}.{k}[{j}]", 0.0001, STAGE)
        for k in ("r", "r2", "h", "tube", "arc", "R", "thick", "side", "depth", "len", "head", "length", "spacing",
                  "tick", "font", "w", "wire", "scale", "start", "label_step"):
            if k in b and not (k == "len" and isinstance(b[k], str)):
                _num(b[k], f"{w}.{k}", -STAGE * 20, STAGE * 20)
        if "opacity" in b:
            _num(b["opacity"], f"{w}.opacity", 0, 1)
        if "count" in b:
            _num(b["count"], f"{w}.count", 1, 200)
        if "turns" in b:
            _num(b["turns"], f"{w}.turns", 1, 60)
        if "major" in b:
            _num(b["major"], f"{w}.major", 1, 1000)
        if kind == "scale" and b.get("length", 1) / b.get("spacing", 0.01) > 2000:
            raise LabError(f"{w}: more than 2000 ticks on a scale")
        if kind == "prism" and isinstance(b.get("angle"), str) and b["angle"] not in params:
            raise LabError(f"{w}.angle: no param '{b['angle']}'")
        if kind == "prism" and "angle" in b and not isinstance(b["angle"], str):
            _num(b["angle"], f"{w}.angle", 0.01, 3.1)
        if kind == "rays" and b.get("var") not in kvars:
            raise LabError(f"{w}.var: rays need a kernel var")
        if kind == "rope" and "bow" in b:
            _bind_spec(b["bow"], f"{w}.bow", kvars, params, kids)
        if kind in ("spring", "rope"):
            for t in ("a", "b"):
                v = b.get(t)
                if isinstance(v, str):
                    if v not in bids:
                        raise LabError(f"{w}.{t}: body '{v}' must be listed earlier")
                elif isinstance(v, dict):
                    _keys(v, {"body", "off"}, f"{w}.{t}")
                    if v.get("body") not in bids:
                        raise LabError(f"{w}.{t}.body: must be a body listed earlier")
                    if "off" in v:
                        _vec(v["off"], f"{w}.{t}.off")
                else:
                    _vec(v, f"{w}.{t}")
        if kind == "wire":
            pts = b.get("pts")
            if not isinstance(pts, list) or not 2 <= len(pts) <= 60:
                raise LabError(f"{w}.pts: 2-60 points")
            for j, q in enumerate(pts):
                _vec(q, f"{w}.pts[{j}]")
            tris += 40 * (len(pts) - 1)
        if kind == "gas":
            tris += 96 * int(b.get("count", 60))
        else:
            tris += TRIS[kind]
        bind = _keys(b.get("bind") or {}, BIND_KEYS, f"{w}.bind")
        for k, spec in bind.items():
            _bind_spec(spec, f"{w}.bind.{k}", kvars, params, kids)
        if "len" in bind and kind != "arrow":
            raise LabError(f"{w}.bind.len: arrows only")
        if "mark" in bind and kind != "scale":
            raise LabError(f"{w}.bind.mark: scales only")
        bids.add(b["id"])
    if tris > MAX_TRIS:
        raise LabError(f"lab: {tris} triangles - a phone allows up to {MAX_TRIS}")

    table = lab.get("table")
    if table is not None:
        _keys(table, TABLE_KEYS, "table")
        cols = table.get("columns")
        if not isinstance(cols, list) or not 1 <= len(cols) <= 8:
            raise LabError("table.columns: 1-8")
        cids = set()
        for i, c in enumerate(cols):
            w = f"table.columns[{i}]"
            _keys(c, COL_KEYS, w)
            if not isinstance(c.get("id"), str) or not IDENT.match(c["id"]) or c["id"] in cids:
                raise LabError(f"{w}.id: needs a unique name")
            cids.add(c["id"])
            _text(c.get("label"), f"{w}.label", 80, need=True)
            src = c.get("from", "manual")
            ok = src == "manual" or (src.startswith("knob:") and src[5:] in kids) or (src.startswith("inst:") and src[5:] in iids)
            if not ok:
                raise LabError(f"{w}.from: 'manual', 'knob:<id>' or 'inst:<id>'")
            for t in ("k", "div"):
                if t in c:
                    _num(c[t], f"{w}.{t}", -1e12, 1e12)
            if c.get("div") == 0:
                raise LabError(f"{w}.div: cannot be 0")
        calc = table.get("calc")
        if calc not in KN.CALCS:
            raise LabError(f"table.calc: unknown '{calc}'")
        miss = set(KN.CALCS[calc]["needs"]) - cids
        if miss:
            raise LabError(f"table: calc '{calc}' needs columns {sorted(miss)}")
        if "truth" in table and not (isinstance(table["truth"], str) and table["truth"].startswith("p.") and table["truth"][2:] in params):
            raise LabError("table.truth: 'p.<param>'")
        if "rows_min" in table:
            _num(table["rows_min"], "table.rows_min", 1, 50)

    tour = lab.get("tour") or []
    if not isinstance(tour, list) or len(tour) > 14:
        raise LabError("lab.tour: <= 14 steps")
    for i, st in enumerate(tour):
        w = f"tour[{i}]"
        _keys(st, TOUR_KEYS, w)
        for k in ("cam", "look"):
            if k in st:
                _vec(st[k], f"{w}.{k}")
        _text(st.get("say"), f"{w}.say", 320, need=True)
        for kid, v in (_keys(st.get("set") or {}, kids, f"{w}.set")).items():
            kn = next(k for k in knobs if k["id"] == kid)
            if not kn["min"] <= _num(v, f"{w}.set.{kid}", -1e9, 1e9) <= kn["max"]:
                raise LabError(f"{w}.set.{kid}: out of the knob's range")

    qs = lab.get("questions") or []
    if not isinstance(qs, list) or len(qs) > 8:
        raise LabError("lab.questions: <= 8")
    for i, q in enumerate(qs):
        w = f"questions[{i}]"
        _keys(q, Q_KEYS, w)
        _text(q.get("q"), f"{w}.q", 300, need=True)
        opts = q.get("options")
        if not isinstance(opts, list) or not 2 <= len(opts) <= 5:
            raise LabError(f"{w}.options: 2-5")
        for j, o in enumerate(opts):
            _text(o, f"{w}.options[{j}]", 160, need=True)
        a = q.get("answer")
        if isinstance(a, bool) or not isinstance(a, int) or not 0 <= a < len(opts):
            raise LabError(f"{w}.answer: must be an option number")
        _text(q.get("why"), f"{w}.why", 400)

    steps = lab.get("steps") or []
    if not isinstance(steps, list) or len(steps) > 16:
        raise LabError("lab.steps: <= 16")
    for i, s in enumerate(steps):
        _text(s, f"steps[{i}]", 300, need=True)
    src = lab.get("sources")
    if not isinstance(src, list) or not src:
        raise LabError("lab.sources: at least one source (where every fact comes from)")
    for i, s in enumerate(src):
        _keys(s, {"title", "note"}, f"sources[{i}]")
        _text(s.get("title"), f"sources[{i}].title", 200, need=True)
        _text(s.get("note"), f"sources[{i}].note", 300)

    chk = lab.get("check")
    if chk is None:
        raise LabError("lab.check: every lab needs a check against its NCERT formula")
    _keys(chk, CHECK_KEYS, "check")
    if chk.get("textbook") not in KN.TEXTBOOK:
        raise LabError(f"check.textbook: unknown '{chk.get('textbook')}'")
    _keys(chk.get("params") or {}, params, "check.params")
    if "rows" in chk:
        if chk.get("calc") not in KN.CALCS or not isinstance(chk["rows"], list) or not chk["rows"]:
            raise LabError("check: rows need a calc")
        for i, r in enumerate(chk["rows"]):
            _keys(r, ROW_KEYS, f"check.rows[{i}]")
    elif not isinstance(chk.get("reading"), str):
        raise LabError("check.reading: needs the name of a measure() reading")
    if "tol" in chk:
        _num(chk["tol"], "check.tol", 1e-9, 0.05)
    return lab


def run_check(lab: dict) -> dict:
    """Run the lab's own NCERT check: the kernel's measurement vs the textbook formula. Returns the numbers."""
    chk = lab["check"]
    name = lab["kernel"]
    base = dict(lab.get("params") or {})
    base.update(chk.get("params") or {})
    p = KN.params_for(name, base)
    cfg = dict(lab.get("cfg") or {})
    K = KN.KERNELS[name]
    if "rows" in chk:
        rows = []
        for r in chk["rows"]:
            q = dict(p)
            q.update({k: float(v) for k, v in (r.get("set") or {}).items()})
            c = dict(cfg)
            if r.get("measure"):
                c["measure"] = r["measure"]
            got = K.measure(q, c)
            row = {col: got[key] for key, col in (r.get("take") or {}).items()}
            row.update(r.get("add") or {})
            rows.append(row)
        measured = KN.calc(chk["calc"], rows, p)
    else:
        c = dict(cfg)
        if chk.get("measure"):
            c["measure"] = chk["measure"]
        measured = float(K.measure(p, c)[chk["reading"]])
    expect = float(KN.TEXTBOOK[chk["textbook"]](p))
    tol = float(chk.get("tol", 0.01))
    err = abs(measured - expect) / max(abs(expect), 1e-12)
    return {"measured": measured, "textbook": expect, "error": err, "tol": tol, "ok": err <= tol}
