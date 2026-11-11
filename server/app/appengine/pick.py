"""v0.825 APP ENGINE 2 (L9 of docs/LOVABLE_STUDIO_PLAN.md): point at the app, change it without a model.

- Click -> source: a preview build tags every element with `data-hs="<file>:<line>:<col>"` (hoola.plugin.mjs). The
  Studio sends that tag here.
- Free style edits (Rs 0, no model call): ONE family at a time (text colour, background, size, weight, padding,
  corners, alignment) and only from the app's own tokens / scale - the class of that family is swapped in the
  element's own `className="..."` string at that exact line, through the same rules as every write, then the preview
  rebuilds. A computed className (cn(...), a template) is refused and named - Hoola changes those in the chat.
- Text edits: only when the element's text is plain words in the source (no {expression}).
- Undo: every free edit keeps the file as it was (last 30), one tap puts it back.
- Error collector: the preview's own errors (preview.js) arrive here, are mapped through the build's hidden source
  map to the app's file and line, kept one card per fingerprint, and an error of an older version is marked "not seen
  since vN" once a newer version has loaded without it."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ..db import now
from . import rules as RL

COLORS = ["ink", "muted", "primary", "primary-ink", "accent", "ok", "warn", "bad", "bg", "surface", "line"]
FAMILIES: dict[str, dict[str, Any]] = {
    "color": {"label": "Text colour", "values": COLORS, "cls": lambda v: f"text-{v}",
              "rx": r"text-(?:" + "|".join(sorted(COLORS, key=len, reverse=True)) + r")(?:/\d+)?"},
    "bg": {"label": "Background", "values": COLORS, "cls": lambda v: f"bg-{v}",
           "rx": r"bg-(?:" + "|".join(sorted(COLORS, key=len, reverse=True)) + r")(?:/\d+)?"},
    "size": {"label": "Text size", "values": ["xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl"], "cls": lambda v: f"text-{v}",
             "rx": r"text-(?:xs|sm|base|lg|xl|2xl|3xl|4xl|5xl)"},
    "weight": {"label": "Weight", "values": ["normal", "medium", "semibold", "bold"], "cls": lambda v: f"font-{v}",
               "rx": r"font-(?:thin|light|normal|medium|semibold|bold|extrabold|black)"},
    "pad": {"label": "Padding", "values": ["0", "1", "2", "3", "4", "6", "8", "10", "12"], "cls": lambda v: f"p-{v}",
            "rx": r"p-\d+(?:\.5)?"},
    "radius": {"label": "Corners", "values": ["none", "control", "card", "full"], "cls": lambda v: f"rounded-{v}",
               "rx": r"rounded(?:-(?:none|sm|md|lg|xl|2xl|3xl|full|control|card))?"},
    "align": {"label": "Align", "values": ["left", "center", "right"], "cls": lambda v: f"text-{v}",
              "rx": r"text-(?:left|center|right|justify)"},
}
FAMILIES_VIEW = {k: {"label": f["label"], "values": f["values"], "classes": [f["cls"](v) for v in f["values"]]}
                 for k, f in FAMILIES.items()}
_HS = re.compile(r"^(src/[\w./-]+\.tsx):(\d+):(\d+)$")
UNDO_KEEP = 30
MAX_ERRORS = 60


class PickError(Exception):
    pass


def parse_hs(hs: str) -> tuple[str, int, int]:
    m = _HS.match(str(hs or "").strip())
    if not m:
        raise PickError("That part has no source tag (it was not written in the app's own .tsx files).")
    return m.group(1), int(m.group(2)), int(m.group(3))


def _offset(text: str, line: int, col: int) -> int:
    lines = text.split("\n")
    if not (1 <= line <= len(lines)) or col < 1:
        raise PickError("That line is not in the file any more - the app changed since the preview was built.")
    return sum(len(x) + 1 for x in lines[: line - 1]) + col - 1


def _open_tag(text: str, at: int) -> tuple[str, int, int]:
    """(tag, start, end) of the opening tag starting at `at` ('<'), skipping quotes and {expressions}."""
    m = re.match(r"<([A-Za-z][A-Za-z0-9-]*)", text[at:])
    if not m:
        raise PickError("The source at that line is not the element any more - the app changed since the preview was built.")
    i, depth, q = at + m.end(), 0, ""
    while i < len(text):
        c = text[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = ""
        elif c in "\"'`":
            q = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == ">" and depth == 0:
            return m.group(1), at, i + 1
        i += 1
    raise PickError("Could not read that element's tag.")


def locate(text: str, hs: str) -> dict[str, Any]:
    _, line, col = parse_hs(hs)
    at = _offset(text, line, col)
    tag, a, b = _open_tag(text, at)
    head = text[a:b]
    cm = re.search(r"""\sclassName\s*=\s*(?:"([^"]*)"|'([^']*)'|(\{))""", head)
    out = {"tag": tag, "start": a, "end": b, "self_closing": head.rstrip().endswith("/>"), "class_kind": "none",
           "classes": []}
    if cm:
        if cm.group(3):
            out["class_kind"] = "computed"
        else:
            val = cm.group(1) if cm.group(1) is not None else cm.group(2)
            out.update(class_kind="string", classes=val.split(), cls_span=(a + cm.start(1 if cm.group(1) is not None else 2),
                                                                             a + cm.end(1 if cm.group(1) is not None else 2)))
    if not out["self_closing"]:
        close = text.find(f"</{tag}>", b)
        inner = text[b:close] if close >= 0 else ""
        out["text_span"] = (b, close) if close >= 0 else None
        out["text"] = inner.strip() if inner and not re.search(r"[<{}]", inner) else None
    else:
        out["text"] = None
    return out


def current(r, hs: str) -> dict[str, Any]:
    """What the style panel shows for one element: its classes, which family value each holds, its plain text."""
    from . import service as S
    rel, _, _ = parse_hs(hs)
    p = S._path_in(r, rel)
    if not p.is_file():
        raise PickError(f"{rel} is not in the app any more.")
    loc = locate(p.read_text("utf-8"), hs)
    vals = {}
    for k, f in FAMILIES.items():
        hit = next((c for c in loc["classes"] if re.fullmatch(f["rx"], c)), "")
        vals[k] = next((v for v in f["values"] if f["cls"](v) == hit), hit and "other")
    return {"hs": hs, "file": rel, "tag": loc["tag"], "classes": loc["classes"], "values": vals,
            "editable_style": loc["class_kind"] in ("string", "none"), "text": loc.get("text"),
            "why": "" if loc["class_kind"] != "computed" else
            "This part's classes are worked out in code (className={...}); ask Hoola in the chat to change it."}


def edit(tenant: str, ref: str, hs: str, style: dict[str, str] | None = None, text: str | None = None) -> dict[str, Any]:
    from . import service as S
    r = S._load(tenant, ref)
    rel, _, _ = parse_hs(hs)
    style = {k: str(v) for k, v in (style or {}).items() if k in FAMILIES}
    for k, v in style.items():
        if v and v not in FAMILIES[k]["values"]:
            raise PickError(f"{FAMILIES[k]['label']}: '{v}' is not one of the app's choices ({', '.join(FAMILIES[k]['values'])}).")
    if not style and text is None:
        raise PickError("Nothing to change.")
    with S._lock(r.id):
        p = S._path_in(r, rel)
        old = p.read_text("utf-8")
        loc = locate(old, hs)
        new = old
        if text is not None:
            t = " ".join(str(text).split())
            if loc.get("text") is None or not loc.get("text_span"):
                raise PickError("That part's words are not plain text in the code (they come from {...}); ask Hoola in the chat.")
            if not t or re.search(r"[<>{}]", t) or len(t) > 400:
                raise PickError("The new words cannot be empty, longer than 400 letters, or use < > { }.")
            a, b = loc["text_span"]
            inner = old[a:b]
            lead = inner[: len(inner) - len(inner.lstrip())]
            trail = inner[len(inner.rstrip()):]
            new = old[:a] + lead + t + trail + old[b:]
            loc = locate(new, hs)                     # the tag before the text did not move
        if style:
            if loc["class_kind"] == "computed":
                raise PickError("This part's classes are worked out in code (className={...}); ask Hoola in the chat to change it.")
            cls = list(loc["classes"])
            for k, v in style.items():
                cls = [c for c in cls if not re.fullmatch(FAMILIES[k]["rx"], c)]
                if v:
                    cls.append(FAMILIES[k]["cls"](v))
            val = " ".join(cls)
            if loc["class_kind"] == "string":
                a, b = loc["cls_span"]
                new = new[:a] + val + new[b:]
            else:
                m = re.match(r"<[A-Za-z][A-Za-z0-9-]*", new[loc["start"]:])
                ins = loc["start"] + m.end()
                new = new[:ins] + f' className="{val}"' + new[ins:]
        if new == old:
            return {"changed": False, "say": "Nothing changed."}
        S._check(r, rel, new)
        _push_undo(r, rel, old)
        res = S._write(r, rel, new)
    return {**res, "hs": hs, "changed": True, "free": True,
            "say": f"Changed {rel} (no AI used, Rs 0). The preview rebuilds in a few seconds; Undo puts it back."}


def _undo_file(r) -> Path:
    from . import service as S
    return S.pdir(r.tenant_id, r.id) / "undo.json"


def _push_undo(r, rel: str, old: str) -> None:
    f = _undo_file(r)
    try:
        stack = json.loads(f.read_text())
    except (OSError, ValueError):
        stack = []
    stack.append({"file": rel, "code": old, "at": now().isoformat()})
    f.write_text(json.dumps(stack[-UNDO_KEEP:]))


def undo(tenant: str, ref: str) -> dict[str, Any]:
    from . import service as S
    r = S._load(tenant, ref)
    with S._lock(r.id):
        f = _undo_file(r)
        try:
            stack = json.loads(f.read_text())
        except (OSError, ValueError):
            stack = []
        if not stack:
            raise PickError("Nothing to undo.")
        last = stack.pop()
        S._write(r, last["file"], last["code"])
        f.write_text(json.dumps(stack))
    return {"file": last["file"], "left": len(stack), "say": f"Put {last['file']} back as it was."}


# ------------------------------------------------------------------ the error collector

_B64 = {c: i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")}


def _vlq(seg: str) -> list[int]:
    out, val, shift = [], 0, 0
    for ch in seg:
        d = _B64[ch]
        val += (d & 31) << shift
        if d & 32:
            shift += 5
            continue
        out.append(-(val >> 1) if val & 1 else val >> 1)
        val, shift = 0, 0
    return out


def map_position(sm: dict[str, Any], line: int, col: int) -> tuple[str, int] | None:
    """(source file, line) for a generated line / column (1-based in, 1-based out) - the nearest mapping at or before."""
    src = sl = 0
    best = None
    for gl, row in enumerate(str(sm.get("mappings") or "").split(";"), 1):
        gc = 0
        for seg in row.split(","):
            if not seg:
                continue
            v = _vlq(seg)
            gc += v[0]
            if len(v) >= 4:
                src += v[1]
                sl += v[2]
                if gl == line and gc <= col - 1:
                    best = (src, sl)
        if gl >= line:
            break
    if best is None:
        return None
    srcs = sm.get("sources") or []
    if not (0 <= best[0] < len(srcs)):
        return None
    name = str(srcs[best[0]]).replace("\\", "/")
    m = re.search(r"(src/[\w./-]+\.(?:tsx|ts))$", name)
    return (m.group(1) if m else name.rsplit("/", 1)[-1]), best[1] + 1


_FRAME = re.compile(r"(?:assets/)([\w.-]+\.js):(\d+):(\d+)")


def map_stack(r, version: int, stack: str) -> tuple[str, int]:
    """The first frame of the app's own code, through the hidden source map of that version's build."""
    from . import service as S
    base = S.ver_dir(r, version) / "dist" / "assets"
    cache: dict[str, Any] = {}
    for m in _FRAME.finditer(stack or ""):
        js = m.group(1)
        if js not in cache:
            try:
                cache[js] = json.loads((base / (js + ".map")).read_text())
            except (OSError, ValueError):
                cache[js] = None
        if cache[js]:
            got = map_position(cache[js], int(m.group(2)), int(m.group(3)))
            if got and got[0].startswith("src/"):
                return got
    return "", 0


def _errors_file(r) -> Path:
    from . import service as S
    return S.pdir(r.tenant_id, r.id) / "errors.json"


def _read_errors(r) -> list[dict[str, Any]]:
    try:
        return json.loads(_errors_file(r).read_text())
    except (OSError, ValueError):
        return []


def record(tenant: str, ref: str, items: list[dict[str, Any]], version: int = 0, loaded: int = 0) -> dict[str, Any]:
    """Errors the preview reported (and, `loaded`, that version N's preview loaded - older errors not seen again are
    marked gone). Masked; at most 20 per call; one card per fingerprint."""
    from . import service as S
    from ..pii import mask_sensitive
    r = S._load(tenant, ref)
    with S._lock(r.id):
        rows = _read_errors(r)
        for it in (items or [])[:20]:
            if not isinstance(it, dict):
                continue
            v = int(it.get("v") or version or r.version or 0)
            kind = str(it.get("kind") or "page")[:12]
            msg = mask_sensitive(str(it.get("m") or "").strip())[:500]
            if not msg:
                continue
            stack = mask_sensitive(str(it.get("s") or ""))[:4000]
            f, ln = map_stack(r, v, stack)
            fp = hashlib.sha1(f"{kind}|{re.sub(r'[0-9]+', '#', msg.lower())[:160]}|{f}|{ln}".encode()).hexdigest()[:16]
            row = next((x for x in rows if x["fp"] == fp), None)
            if row is None:
                row = {"fp": fp, "kind": kind, "message": msg, "file": f, "line": ln, "count": 0, "first_at": now().isoformat(),
                       "state": "open", "page": str(it.get("p") or "/")[:140]}
                rows.append(row)
            row.update(count=row["count"] + 1, last_at=now().isoformat(), version=v, state="open" if row["state"] != "dismissed" else "dismissed")
        if loaded:
            for x in rows:
                if x["state"] == "open" and int(x.get("version") or 0) < int(loaded):
                    x.update(state="gone", gone_in=int(loaded))
        rows = sorted(rows, key=lambda x: x.get("last_at") or "", reverse=True)[:MAX_ERRORS]
        _errors_file(r).write_text(json.dumps(rows))
    return {"open": [x for x in rows if x["state"] == "open"]}


def errors(tenant: str, ref: str) -> list[dict[str, Any]]:
    from . import service as S
    return _read_errors(S._load(tenant, ref))


def set_state(tenant: str, ref: str, fp: str, state: str) -> dict[str, Any]:
    from . import service as S
    if state not in ("dismissed", "open"):
        raise PickError("state is dismissed or open")
    r = S._load(tenant, ref)
    with S._lock(r.id):
        rows = _read_errors(r)
        row = next((x for x in rows if x["fp"] == fp), None)
        if row is None:
            raise PickError("No such error.")
        row["state"] = state
        _errors_file(r).write_text(json.dumps(rows))
    return row


def open_block(r) -> str:
    rows = [x for x in _read_errors(r) if x["state"] == "open"][:3]
    if not rows:
        return ""
    return ("\nThe preview reported these errors (fix them first if her message is about them):\n" +
            "\n".join(f"- {x['message']}" + (f" (at {x['file']}:{x['line']})" if x.get("file") else "") +
                      f" [seen {x['count']}x in version {x.get('version')}]" for x in rows))

