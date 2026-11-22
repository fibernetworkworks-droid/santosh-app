"""v0.999.76 D7 EDIT FOREVER (docs/WEB_DESIGN_ENGINE_PLAN.md P9): her own changes to a written React website, kept as
DATA beside the code, so they survive every later write (a review round, a new build from her prototype).

Two files in the app's `.hoola/` folder:
  design.json   the design choices the D5/D6 loop ended with (layout / background / left out per section) + the custom
                sections already written (so the site can be written again with NO model call)
  edits.json    HER changes, which always win: words she changed (section + the path of the words in that section's
                props + the new words), her section choices (layout / background / leave out) and (v0.999.130) her
                pictures (section + the path of the picture + one of HER website's photos, or none, + its description);
                the last 30 kept for Undo

Writing the site again from these is code only (writer.write_app with model=None): Rs 0. Her phone, address, hours and
email are changed once in Settings (writer.NOT_WORDS), so a section never disagrees with the rest of the site."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

MAX_UNDO = 30
MAX_WORDS = 600
MAX_ALT = 200


def _dir(tenant: str, ref: str) -> Path:
    from . import service as AE
    d = AE.src_dir(AE._load(tenant, ref)) / ".hoola"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read(f: Path, empty: dict[str, Any]) -> dict[str, Any]:
    try:
        v = json.loads(f.read_text("utf-8"))
        return v if isinstance(v, dict) else dict(empty)
    except (OSError, ValueError):
        return json.loads(json.dumps(empty))


def design(tenant: str, ref: str) -> dict[str, Any]:
    return _read(_dir(tenant, ref) / "design.json", {"design": {}, "custom": {}})


def save_design(tenant: str, ref: str, design_: dict[str, Any], custom: dict[str, str]) -> None:
    (_dir(tenant, ref) / "design.json").write_text(json.dumps({"design": design_, "custom": custom}, indent=1), "utf-8")


def edits(tenant: str, ref: str) -> dict[str, Any]:
    return _read(_dir(tenant, ref) / "edits.json", {"words": {}, "sections": {}, "pictures": {}, "undo": []})


def _save_edits(tenant: str, ref: str, e: dict[str, Any]) -> None:
    e["undo"] = (e.get("undo") or [])[-MAX_UNDO:]
    (_dir(tenant, ref) / "edits.json").write_text(json.dumps(e, indent=1, ensure_ascii=False), "utf-8")


def _snap(e: dict[str, Any]) -> dict[str, Any]:
    return {"words": json.loads(json.dumps(e.get("words") or {})), "sections": json.loads(json.dumps(e.get("sections") or {})),
            "pictures": json.loads(json.dumps(e.get("pictures") or {}))}


def put_words(tenant: str, ref: str, sec: str, path: list[Any], value: str, was: str = "") -> dict[str, Any]:
    e = edits(tenant, ref)
    e.setdefault("undo", []).append({**_snap(e), "at": time.time(), "what": f"words in {sec}"})
    lst = [x for x in (e.setdefault("words", {}).get(sec) or []) if list(x.get("path") or []) != list(path)]
    lst.append({"path": list(path), "value": value[:MAX_WORDS], "was": was[:MAX_WORDS]})
    e["words"][sec] = lst
    _save_edits(tenant, ref, e)
    return e


def put_section(tenant: str, ref: str, sec: str, choice: dict[str, Any]) -> dict[str, Any]:
    e = edits(tenant, ref)
    e.setdefault("undo", []).append({**_snap(e), "at": time.time(), "what": f"section {sec}"})
    cur = dict((e.setdefault("sections", {}).get(sec)) or {})
    for k in ("variant", "tone"):
        if choice.get(k):
            cur[k] = str(choice[k])
    if "drop" in choice:                             # False is kept: she brought back a section the review left out
        cur["drop"] = bool(choice["drop"])
    e["sections"][sec] = cur
    _save_edits(tenant, ref, e)
    return e


def put_picture(tenant: str, ref: str, sec: str, path: list[Any], src: str | None, alt: str | None,
                was: str = "") -> dict[str, Any]:
    """v0.999.130: her picture at that place of the section - `src` one of her website's photos (./photos/<name>.webp)
    or "" for none (the design's own stand-in), None = keep the picture; `alt` its description, None = keep it."""
    e = edits(tenant, ref)
    e.setdefault("undo", []).append({**_snap(e), "at": time.time(), "what": f"picture in {sec}"})
    lst = e.setdefault("pictures", {}).get(sec) or []
    cur = next((x for x in lst if list(x.get("path") or []) == list(path)), None)
    if cur is None:
        cur = {"path": list(path), "was": was[:200]}
        lst.append(cur)
    if src is not None:
        cur["src"] = src
    if alt is not None:
        cur["alt"] = alt[:MAX_ALT]
    e["pictures"][sec] = lst
    _save_edits(tenant, ref, e)
    return e


def undo(tenant: str, ref: str) -> dict[str, Any] | None:
    e = edits(tenant, ref)
    if not e.get("undo"):
        return None
    last = e["undo"].pop()
    e["words"], e["sections"] = last.get("words") or {}, last.get("sections") or {}
    e["pictures"] = last.get("pictures") or {}
    _save_edits(tenant, ref, e)
    return {"undone": last.get("what") or "the last change", **e}


def merged(tenant: str, ref: str) -> tuple[dict[str, dict[str, Any]], dict[str, str], dict[str, list[dict[str, Any]]]]:
    """(design with her section choices on top, custom sections already written, her words + her pictures - a picture
    rides with the words of its section as {"kind": "picture", ...}, so every page in every language gets it)."""
    d = design(tenant, ref)
    e = edits(tenant, ref)
    out = json.loads(json.dumps(d.get("design") or {}))
    for sec, ch in (e.get("sections") or {}).items():
        base = dict(out.get(sec) or {})
        base.update(ch)
        if base.get("drop") is False:
            base.pop("drop")
        out[sec] = base
    words = {k: list(v) for k, v in (e.get("words") or {}).items()}
    for sec, pics in (e.get("pictures") or {}).items():
        words[sec] = words.get(sec, []) + [{"kind": "picture", **x} for x in pics]
    return out, dict(d.get("custom") or {}), words


def custom_on_disk(tenant: str, ref: str, pages: list[dict[str, Any]]) -> dict[str, str]:
    """The custom sections already written into the app (so writing again never calls the model)."""
    from . import service as AE
    from . import writer as W
    root = AE.src_dir(AE._load(tenant, ref)) / "src" / "components" / "sections"
    out: dict[str, str] = {}
    for pg in pages:
        for s in pg.get("sections") or []:
            t = str(s.get("type") or "")
            if t.startswith("custom_") or t not in W.MAPPERS:
                comp = W.custom_component(s)
                if (root / f"{comp}.tsx").is_file():
                    out[f"{pg['slug']}:{t}"] = comp
    return out
