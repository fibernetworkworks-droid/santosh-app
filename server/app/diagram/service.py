"""HOOLA DIAGRAM D2 - one diagram, start to finish, in Hoola chat (docs/DIAGRAM_TOOL_PLAN.md §2, §4).

The model writes only the DESCRIPTION; the engine draws it and checks it:
  A archify          the description is archify's JSON for one of its 10 types; archify's code places the boxes and lines
                     and its four gates check the page
  B diagram-design   the description is the full HTML page from diagram-design's template; its two checkers check it

draw():  route the type to its engine (code decides; a named engine must fit) -> run that engine's checks -> a failing
         check goes back to the model with the exact problems (same diagram id, at most MAX_ROUNDS rounds) -> a passing
         diagram is rendered to a picture the model LOOKS at before it answers, and saved as a page (an artifact: the
         console workspace + the phone viewer open it; versions; share). Still failing after the last round = saved
         WITH its open problems named when there is a page to show, never a quiet "done".
update(): the same diagram id, a change to its description (exact old -> new, or the whole new description), redrawn
         through the same checks as a new version of the same page.

Every try lives in data/diagram/work/<tenant>/<diagram id>/ (description, the engine's output, its receipt, the
picture); the diagram's meta (engine, type, artifact id, rounds) beside it."""
from __future__ import annotations

import json
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from . import runners as R
from . import vendor as V

MAX_ROUNDS = 3
DESC_FILE = {"archify": "description.json", "diagram-design": "description.html", "drawio": "description.drawio"}
EDITABLE_WORDS = ("drawio", "draw.io", "draw-io", "editable", "editable diagram")
MAX_DESC = 400_000            # one description (archify JSON or a diagram-design page)
MAX_PAGE = 3_000_000          # the built page (archify's viewer is ~1 MB)
_LOCK = threading.RLock()

# diagram-design type ids that are archify's job (archify places boxes + routes lines in code = the main engine)
TO_ARCHIFY = {"architecture": "architecture", "sequence": "sequence", "state": "lifecycle", "er": "erd",
              "tree": "tree", "timeline": "timeline", "uml-class": "class", "data-flow": "dataflow",
              "process": "workflow"}
ALIASES = {
    "flow chart": "flowchart", "decision tree": "flowchart", "org": "org-chart", "org chart": "org-chart",
    "organisation chart": "org-chart", "organization chart": "org-chart", "funnel": "pyramid", "pyramid": "pyramid",
    "erd": "erd", "er diagram": "erd", "entity relationship": "erd", "data model": "erd", "database": "db-schema",
    "state machine": "lifecycle", "state": "lifecycle", "status": "lifecycle", "lifecycle": "lifecycle",
    "class diagram": "class", "uml": "class", "data flow": "dataflow", "pipeline": "dataflow", "etl": "dataflow",
    "workflow": "workflow", "process": "workflow", "runbook": "workflow", "approval": "workflow",
    "sequence diagram": "sequence", "api calls": "sequence", "gantt chart": "gantt", "roadmap": "gantt",
    "journey": "journey", "user journey": "journey", "customer journey": "journey", "mind map": "tree",
    "hierarchy": "tree", "bar chart": "bar", "bar": "bar", "line chart": "line", "pie": "treemap",
    "flywheel": "loop", "cycle": "loop", "2x2": "quadrant", "matrix": "quadrant", "fishbone": "fishbone",
    "root cause": "fishbone", "venn": "venn", "sankey": "sankey", "swimlane": "swimlane", "swim lane": "swimlane",
    "kanban": "kanban", "waterfall chart": "dd:waterfall", "budget bridge": "dd:waterfall",
    "money bridge": "dd:waterfall", "bridge chart": "dd:waterfall", "budget-bridge": "dd:waterfall",
}


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def on() -> bool:
    return bool(_set("diagram_enabled", True))


def root() -> Path:
    return Path("data") / "diagram" / "work"


def _tdir(tenant: str) -> Path:
    return root() / (re.sub(r"[^A-Za-z0-9_-]", "", tenant or "") or "x")


def _ddir(tenant: str, did: str) -> Path:
    return _tdir(tenant) / (re.sub(r"[^a-z0-9-]", "", did or "") or "x")


def _meta(tenant: str, did: str) -> dict[str, Any] | None:
    f = _ddir(tenant, did) / "meta.json"
    try:
        return json.loads(f.read_text("utf-8"))
    except (OSError, ValueError):
        return None


def _save_meta(tenant: str, m: dict[str, Any]) -> None:
    d = _ddir(tenant, m["id"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(d / "meta.json")


# ------------------------------------------------------------------ the type router (code decides)
def catalogue() -> list[dict[str, str]]:
    """Every type the engines draw: archify's 10 first, then diagram-design's types that archify does not cover."""
    out = [{"type": t["type"], "engine": "archify", "use": t["use"]} for t in V.archify_types()]
    archify = {t["type"] for t in V.archify_types()}
    for t in V.dd_types():
        if t["type"] in TO_ARCHIFY:
            continue
        name = t["type"] if t["type"] not in archify else "budget-bridge" if t["type"] == "waterfall" else "dd:" + t["type"]
        out.append({"type": name, "engine": "diagram-design", "use": f"{t['name']}: {t['use']}"})
    out.append({"type": "drawio", "engine": "drawio",
                "use": "an EDITABLE draw.io diagram she changes by hand too (drag, rename, restyle; select shapes and ask "
                       "for changes to only those) - any kind: flows, architecture with AWS / Azure / GCP / Kubernetes "
                       "icons, BPMN, swimlanes, tables, networks"})
    return out


def route(kind: str, engine: str = "") -> tuple[str, str, str]:
    """(engine, type, note). The type the model names is matched to its engine by code; a named engine is kept only
    when that engine really draws the type. ('', '', reason) when no engine draws it."""
    k = re.sub(r"\s+", " ", str(kind or "").strip().lower().replace("_", "-"))
    k = ALIASES.get(k, ALIASES.get(k.replace("-", " "), k))
    a = {t["type"] for t in V.archify_types()}
    d = {t["type"] for t in V.dd_types()}
    e = str(engine or "").strip().lower()
    if e in ("a", "archify"):
        e = "archify"
    elif e in ("b", "diagram-design", "diagram_design", "design"):
        e = "diagram-design"
    note = ""
    if e in ("c", "drawio", "draw.io", "draw-io", "editable") or k in EDITABLE_WORDS:
        return "drawio", "drawio", ""
    if k.startswith("dd:") and k[3:] in d:          # a diagram-design type whose id archify also uses (waterfall)
        return "diagram-design", k[3:], ""
    if k in a or k in TO_ARCHIFY:
        t = k if k in a else TO_ARCHIFY[k]
        if e == "diagram-design" and k in d:
            return "diagram-design", k, ""
        if e == "diagram-design":
            note = f"diagram-design has no '{k}' type, so archify draws it."
        return "archify", t, note
    if k in d:
        if e == "archify":
            note = f"archify does not draw '{k}', so diagram-design draws it."
        return "diagram-design", k, note
    return "", "", (f"No engine draws '{kind}'. Pick one of: " +
                    ", ".join(sorted(a | {t for t in d if t not in TO_ARCHIFY})))


# ------------------------------------------------------------------ guides (the engine's own words, read on demand)
def _md_sections(text: str, heads: tuple[str, ...]) -> str:
    out = []
    for h in heads:
        i = text.find(h)
        if i < 0:
            continue
        j = text.find("\n## ", i + len(h))
        out.append(text[i:j if j > 0 else len(text)].strip())
    return "\n\n".join(out)


HOOLA_RULES = ("HOOLA RULES (on top of the engine's own): write every label, title and note in HER language (the "
               "language she writes in; any script - right-to-left scripts stay right to left, numbers and code stay "
               "left to right); use only facts she gave or that you read - an unknown becomes a short [blank], never "
               "an invented number or name; before you call draw, tell her the plan in ONE line (type, what is in it, "
               "what you leave out) and draw at once; after a check fails, fix exactly the problems it names and call "
               "draw again with the same diagram_id.")


def guide(kind: str, engine: str = "") -> dict[str, Any]:
    eng, t, note = route(kind, engine)
    if not eng:
        return {"ok": False, "error": note}
    if eng == "drawio":
        src = V.DRAWIO_AI / "src"
        text = ("ENGINE draw.io (editable) - she can change it by hand afterwards.\n\nWHAT YOU WRITE: the diagram's "
                "<mxCell> elements (or a whole one-page <mxfile>) as plain, uncompressed draw.io XML: shapes with "
                "vertex=\"1\" parent=\"1\" and an <mxGeometry x y width height as=\"geometry\"/>, connectors with "
                "edge=\"1\" source / target ids and <mxGeometry relative=\"1\" as=\"geometry\"/>; ids short and "
                "unique; the two root cells 0 and 1 are added for you. Place shapes on a grid with room between them "
                "(no overlaps; leave 40+ px between boxes); labels short. Labels and links are TEXT only - no script, no "
                "javascript: link. Pass it as `content` to diagram action=draw with type drawio.\n\nTO CHANGE IT LATER: "
                "action=read first (you get every cell and the shapes she has SELECTED), then action=change with ops "
                "id by id ({op: update | add | delete, id, value / style / x / y / width / height / source / target}) - "
                "never redraw what she drew by hand. If she selected shapes and says 'these', change only those.\n\n"
                f"{HOOLA_RULES}\n\n=== next-ai-draw-io's drawing guide (its TypeScript source; the strings are the rules) ===\n"
                f"{(src / 'drawing-guide.ts').read_text('utf-8')}\n\n=== xml-examples.ts ===\n"
                f"{(src / 'xml-examples.ts').read_text('utf-8')}\n\n=== xml-reference.ts ===\n"
                f"{(src / 'xml-reference.ts').read_text('utf-8')}")
        return {"ok": True, "engine": "drawio", "type": "drawio", "note": note, "guide": text[:68000]}
    if eng == "archify":
        info = next(x for x in V.archify_types() if x["type"] == t)
        schema = (V.ARCHIFY / info["schema"]).read_text("utf-8")
        common = (V.ARCHIFY / "schemas" / "common.schema.json").read_text("utf-8")
        example = (V.ARCHIFY / info["example"]).read_text("utf-8")
        defaults = (V.ARCHIFY / "references" / "authoring-defaults.md").read_text("utf-8")
        text = (f"ENGINE archify - type '{t}': {info['use']}\n\nWHAT YOU WRITE: one JSON object (the 'candidate') that "
                f"follows the schema below; archify's own code places every box and routes every line, so write "
                "NO coordinates. Pass it as `content` to diagram action=draw (a JSON string or object). Keep meta.title "
                "short; leave meta.quality_profile out (Hoola runs the strict 'showcase' gates).\n\n"
                f"{HOOLA_RULES}\n\n=== archify authoring defaults (references/authoring-defaults.md) ===\n{defaults}\n\n"
                f"=== schema {info['schema']} ===\n{schema}\n\n=== schemas/common.schema.json ===\n{common}\n\n"
                f"=== example {info['example']} ===\n{example}")
    else:
        info = next(x for x in V.dd_types() if x["type"] == t)
        skill = (V.DD / "SKILL.md").read_text("utf-8")
        core = _md_sections(skill, ("## 1. Philosophy", "## 4. Universal Anti-patterns", "## 6. Core SVG Primitives",
                                    "## 7. Layout & Spacing", "## 12. Output"))
        text = (f"ENGINE diagram-design - type '{t}' ({info['name']}): {info['use']}\n\nWHAT YOU WRITE: ONE complete, "
                "self-contained HTML page (<!doctype html> ... </html>) made from the template below, with the "
                "inline SVG for this type. Name the svg ids `<slug>-title` / `<slug>-desc` with one short slug (e.g. "
                "`hiring-funnel`); the file is saved under that slug and the checker matches them. Pass the page as "
                "`content` to diagram action=draw. Resolve every {token} placeholder to the style guide's hex value; "
                "no outside scripts or images.\n\n"
                f"{HOOLA_RULES}\n\n=== the engine's core rules (SKILL.md) ===\n{core}\n\n"
                f"=== type reference {info['reference']} ===\n{(V.DD / info['reference']).read_text('utf-8')}\n\n"
                f"=== assets/template.html ===\n{(V.DD / 'assets' / 'template.html').read_text('utf-8')}\n\n"
                f"=== references/primitives-core.md ===\n{(V.DD / 'references' / 'primitives-core.md').read_text('utf-8')}\n\n"
                f"=== references/style-guide.md ===\n{(V.DD / 'references' / 'style-guide.md').read_text('utf-8')}")
    return {"ok": True, "engine": eng, "type": t, "note": note, "guide": text}


# ------------------------------------------------------------------ draw / update
def _new_id() -> str:
    return "dg-" + secrets.token_hex(5)


def _as_json(content: Any) -> tuple[dict | None, str]:
    if isinstance(content, dict):
        return content, ""
    s = str(content or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        v = json.loads(s)
    except ValueError as e:
        return None, f"the description is not valid JSON ({e})"
    if not isinstance(v, dict):
        return None, "the description must be one JSON object"
    return v, ""


def _as_html(content: Any) -> tuple[str, str, str]:
    """(page, slug, problem) for a diagram-design page."""
    s = str(content or "").strip()
    s = re.sub(r"^```(?:html)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    if not re.search(r"<!doctype html", s, re.I) or "</html>" not in s.lower():
        return "", "", "write the WHOLE page: from <!doctype html> to </html>, made from the template"
    if not re.search(r"<svg\b", s, re.I):
        return "", "", "the page has no <svg> - the diagram goes in one inline svg"
    m = re.search(r'id="([a-z0-9][a-z0-9-]{0,60})-title"', s)
    slug = m.group(1) if m else "diagram"
    return s, slug, ""


def _picture(png: Path, out: Path) -> str:
    """A smaller JPEG copy of the picture for the model to look at (longest side <= 1400 px). '' if it cannot."""
    try:
        from PIL import Image
        im = Image.open(png).convert("RGB")
        im.thumbnail((1400, 1400))
        im.save(out, "JPEG", quality=82)
        return str(out)
    except Exception:  # noqa: BLE001
        return str(png) if png.is_file() else ""


def _try(tenant: str, m: dict[str, Any], desc: Any) -> dict[str, Any]:
    """Run the engine once on this description. {ok, html, problems, png, desc_text}."""
    n = int(m.get("tries", 0)) + 1
    m["tries"] = n
    work = _ddir(tenant, m["id"]) / f"try-{n}"
    work.mkdir(parents=True, exist_ok=True)
    if m["engine"] == "drawio":
        return _try_drawio(m, work, desc)
    if m["engine"] == "archify":
        cand, bad = _as_json(desc)
        if cand is None:
            return {"ok": False, "html": "", "problems": [bad], "png": "", "desc_text": str(desc or "")}
        text = json.dumps(cand, ensure_ascii=False, indent=2)
        if len(text) > MAX_DESC:
            return {"ok": False, "html": "", "problems": ["the description is too large"], "png": "", "desc_text": ""}
        q = (cand.get("meta") or {}).get("quality_profile") if isinstance(cand.get("meta"), dict) else None
        slug = re.sub(r"[^a-z0-9-]+", "-", (m.get("title") or m["type"]).lower()).strip("-")[:40] or m["type"]
        r = R.archify_finalize(m["type"], cand, work, slug=slug, quality="standard" if q == "standard" else "showcase")
        probs = list(r.get("problems") or [])
        hint = [h for h in (r.get("review") or [])][:4]
        res = {"ok": bool(r.get("ok")), "html": r.get("html") or "", "problems": probs, "hints": hint,
               "gates": r.get("gates") or {}, "png": "", "desc_text": text}
        if res["ok"]:
            p = R.page_png(res["html"], work / "picture.png")
            res["png"] = p.get("png") or ""
        return res
    page, slug, bad = _as_html(desc)
    if bad:
        return {"ok": False, "html": "", "problems": [bad], "png": "", "desc_text": str(desc or "")}
    if len(page) > MAX_DESC:
        return {"ok": False, "html": "", "problems": ["the page is too large"], "png": "", "desc_text": ""}
    f = work / f"{slug}.html"
    f.write_text(page, "utf-8")
    c = R.dd_check([f])
    probs = [p for lst in c.get("failed", {}).values() for p in lst][:20]
    res = {"ok": bool(c.get("ok")), "html": str(f), "problems": probs, "png": "", "desc_text": page}
    p = R.dd_png(f, work / "picture.png")
    res["png"] = p.get("png") or ""
    if not res["png"] and res["ok"]:
        res["problems"] = ["the page passed the checks but could not be rendered to a picture: " + str(p.get("said"))[:300]]
    return res


def drawio_page(title: str, svg: str) -> str:
    """The page every viewer shows for an editable diagram: the editor's own SVG export (it carries the diagram too)."""
    import html as _h
    i = svg.find("<svg")
    body = svg[i:] if i >= 0 else ""
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            "content=\"width=device-width, initial-scale=1\"><title>" + _h.escape(title or "Diagram") + "</title><style>"
            ":root{color-scheme:light dark}body{margin:0;padding:16px;display:grid;place-items:center;min-height:90vh;"
            "background:#fff}svg{max-width:100%;height:auto}</style></head><body>" + body + "</body></html>")


def _try_drawio(m: dict[str, Any], work: Path, desc: Any) -> dict[str, Any]:
    from . import drawio as DR
    from . import drawio_xml as X
    xml, probs = X.normalize(str(desc or ""), m.get("title") or "Page-1")
    if probs:
        return {"ok": False, "html": "", "problems": probs, "png": "", "desc_text": str(desc or "")}
    if not DR.ready():
        return {"ok": False, "html": "", "png": "", "desc_text": xml,
                "problems": ["the draw.io editor is not set up on this server (vps-ops diagram_setup) - say so plainly"]}
    svg = R.drawio_export(xml, work / "diagram.svg", "xmlsvg")
    png = R.drawio_export(xml, work / "picture.png", "png")
    if not svg.get("ok"):
        return {"ok": False, "html": "", "png": "", "desc_text": xml,
                "problems": ["draw.io could not draw it: " + str(svg.get("said") or "")[:200]]}
    page = work / "page.html"
    page.write_text(drawio_page(m.get("title", ""), Path(svg["file"]).read_text("utf-8")), "utf-8")
    return {"ok": True, "html": str(page), "problems": [], "png": png.get("file") or "", "desc_text": xml}


def publish_drawio(tenant: str, conv: str, m: dict[str, Any], xml: str, page: str, note: str = "") -> dict[str, Any]:
    from .. import artifacts
    row = artifacts.save_built(tenant, conv, title=m.get("title") or "Diagram", page=page, source=xml, kind="diagram",
                               summary="Diagram · editable (draw.io)", artifact_id=m.get("artifact_id") or "",
                               note=note or "diagram: drawio")
    m["artifact_id"] = row["id"]
    m["version"] = row.get("version")
    return row


def _publish(tenant: str, conv: str, m: dict[str, Any], res: dict[str, Any], open_problems: list[str]) -> dict[str, Any]:
    from .. import artifacts
    page = Path(res["html"]).read_text("utf-8")
    if len(page) > MAX_PAGE:
        raise ValueError("the drawn page is too large to keep")
    label = next((t["name"] for t in V.dd_types() if t["type"] == m["type"]), m["type"].replace("-", " ").title()) \
        if m["engine"] == "diagram-design" else "editable (draw.io)" if m["engine"] == "drawio" \
        else m["type"].replace("-", " ").title()
    summary = f"Diagram · {label}" + (" · has open problems" if open_problems else "")
    row = artifacts.save_built(tenant, conv, title=m.get("title") or label, page=page, source=res["desc_text"],
                               kind="diagram", summary=summary, artifact_id=m.get("artifact_id") or "",
                               note=("diagram: " + m["engine"] + (" (open problems)" if open_problems else "")))
    m["artifact_id"] = row["id"]
    m["version"] = row.get("version")
    return row


def _answer(m: dict[str, Any], res: dict[str, Any], row: dict[str, Any] | None, open_problems: list[str],
            note: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {"ok": True, "diagram_id": m["id"], "engine": m["engine"], "type": m["type"],
                           "title": m.get("title", "")}
    if row:
        out.update({"artifact_id": row["id"], "version": row.get("version"), "shown": True})
    if res.get("gates"):
        out["checks"] = res["gates"]
    if open_problems:
        out["open_problems"] = open_problems[:12]
        out["said"] = (f"Shown to her WITH open problems after {MAX_ROUNDS} rounds - tell her plainly what is still "
                       "wrong (open_problems); do not call it done.")
    else:
        out["said"] = ("Drawn and checked by the engine. The picture is attached: LOOK at it. If something reads wrong "
                       "(a label cut, a missing part, wrong words), fix it with action=update and this diagram_id; if it "
                       "is right, tell her in one or two sentences what it shows - she opens the card herself.")
    if res.get("hints"):
        out["layout_hints"] = res["hints"]
    if note:
        out["note"] = note
    if res.get("png"):
        look = _picture(Path(res["png"]), Path(res["png"]).with_name("look.jpg"))
        if look:
            out["_look"] = look            # santosh turns this into a picture block the model sees (never into text)
    return out


GATE = ("She changed this diagram by hand since you last read it. Call diagram action=read with this diagram_id, "
        "then make your change on what is there now - never on an older copy.")


def _gate(m: dict[str, Any]) -> str:
    """'' when Hoola may change this editable diagram: it read it after her last change."""
    if m.get("engine") != "drawio":
        return ""
    return "" if int(m.get("ai_seen_rev") or 0) >= int(m.get("rev") or 0) else GATE


def _after_ai_drawio(m: dict[str, Any], xml: str, ids: list[str], ops: list | None = None) -> None:
    """A change by Hoola: next revision, Hoola has seen it, and it goes out once to her open editor."""
    from . import drawio_xml as X
    from . import live as L
    rev = int(m.get("rev") or 0) + 1
    m.update({"rev": rev, "ai_seen_rev": rev, "last_by": "ai"})
    L.push(m, rev, ids, ops=ops, model="" if ops else X.model_of(xml))


def draw(tenant: str, conv: str, kind: str, title: str, content: Any, engine: str = "",
         diagram_id: str = "", from_id: str = "") -> dict[str, Any]:
    if not on():
        return {"ok": False, "error": "Diagrams are switched off on this server (diagram_enabled)."}
    with _LOCK:
        if diagram_id:
            m = _meta(tenant, diagram_id)
            if m is None:
                return {"ok": False, "error": f"No diagram {diagram_id} here; start a new one without diagram_id."}
            g = _gate(m)
            if g:
                return {"ok": False, "diagram_id": diagram_id, "reason": "she changed it since you read it", "said": g}
            note = ""
            if kind:
                eng, t, note = route(kind, engine)
                if eng and (eng, t) != (m["engine"], m["type"]):
                    m.update({"engine": eng, "type": t, "fails": 0})
        else:
            eng, t, note = route(kind, engine)
            if not eng:
                return {"ok": False, "error": note}
            m = {"id": _new_id(), "engine": eng, "type": t, "title": str(title or "").strip()[:120], "fails": 0,
                 "tries": 0, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "conversation_id": conv}
            src = _meta(tenant, from_id) if from_id else None
            if src is not None:
                m["from"] = from_id
                m["title"] = m["title"] or src.get("title", "")
        if title:
            m["title"] = str(title).strip()[:120]
        _save_meta(tenant, m)
    res = _try(tenant, m, content)
    m["desc_kind"] = {"archify": "json", "drawio": "drawio"}.get(m["engine"], "html")
    if res["ok"]:
        m["fails"] = 0
        with _LOCK:
            row = _publish(tenant, conv, m, res, [])
            _save_desc(tenant, m, res["desc_text"])
            if m["engine"] == "drawio":
                from . import drawio_xml as X
                _after_ai_drawio(m, res["desc_text"], [c["id"] for c in X.listing(res["desc_text"])])
                if m.get("from"):
                    src = _meta(tenant, m["from"])
                    if src is not None:
                        src["editable_id"] = m["id"]
                        _save_meta(tenant, src)
            _save_meta(tenant, m)
        out = _answer(m, res, row, [], note)
        if m["engine"] == "drawio":
            from . import live as L
            out["editor"] = L.link(tenant, m["id"])
            out["said"] += " It is EDITABLE: she can open it and change it by hand (Edit by hand on the card)."
        return out
    m["fails"] = int(m.get("fails", 0)) + 1
    _save_meta(tenant, m)
    if m["fails"] < MAX_ROUNDS:
        return {"ok": False, "diagram_id": m["id"], "engine": m["engine"], "type": m["type"],
                "round": m["fails"], "rounds_left": MAX_ROUNDS - m["fails"], "problems": res["problems"][:20],
                "hints": res.get("hints") or [], "checks": res.get("gates") or {},
                "reason": "the engine's check did not pass yet",
                "said": ("Not shown yet: the engine's check found the problems listed. Fix exactly those and call "
                         f"diagram action=draw again with diagram_id {m['id']} and the whole corrected description "
                         f"(round {m['fails']} of {MAX_ROUNDS})."), **({"note": note} if note else {})}
    # the last round failed too: show it with the problems named when there is a page, else say it plainly
    m["fails"] = 0
    if res.get("html") and Path(res["html"]).is_file():
        row = _publish(tenant, conv, m, res, res["problems"])
        _save_desc(tenant, m, res["desc_text"])
        _save_meta(tenant, m)
        return _answer(m, res, row, res["problems"], note)
    _save_meta(tenant, m)
    return {"ok": False, "diagram_id": m["id"], "problems": res["problems"][:12],
            "reason": f"the engine could not draw it after {MAX_ROUNDS} rounds",
            "said": "Tell her plainly it could not be drawn and why (problems); offer a simpler diagram."}


def _save_desc(tenant: str, m: dict[str, Any], text: str) -> None:
    (_ddir(tenant, m["id"]) / DESC_FILE.get(m["engine"], "description.html")).write_text(text, "utf-8")


def current(tenant: str, did: str) -> tuple[dict[str, Any] | None, str]:
    m = _meta(tenant, did)
    if m is None:
        return None, ""
    f = _ddir(tenant, did) / DESC_FILE.get(m["engine"], "description.html")
    return m, (f.read_text("utf-8") if f.is_file() else "")


def update(tenant: str, conv: str, diagram_id: str, edits: list[dict] | None = None, content: Any = None,
           title: str = "") -> dict[str, Any]:
    m, desc = current(tenant, diagram_id)
    if m is None:
        return {"ok": False, "error": f"No diagram {diagram_id} here (it is made by diagram action=draw)."}
    if not desc:
        return {"ok": False, "error": "This diagram has no saved description yet; draw it first."}
    if content not in (None, ""):
        new = content
    elif edits:
        from ..artifacts import EditError, apply_edits
        try:
            new = apply_edits(desc, edits, m.get("title", ""), int(m.get("version") or 0))
        except EditError as e:
            return {"ok": False, "error": str(e), "diagram_id": diagram_id}
    else:
        return {"ok": False, "error": "update needs edits [{old_str, new_str}] (exact text from the description) or "
                                      "content (the whole new description)."}
    return draw(tenant, conv, "", title, new, diagram_id=diagram_id)


def listing(tenant: str, limit: int = 20) -> list[dict[str, Any]]:
    out = []
    d = _tdir(tenant)
    if not d.is_dir():
        return out
    for sub in sorted(d.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        m = _meta(tenant, sub.name)
        if m:
            out.append({k: m.get(k) for k in ("id", "title", "engine", "type", "artifact_id", "version")})
    return out


def by_artifact(tenant: str, artifact_id: str) -> dict[str, Any] | None:
    """The diagram behind a page (her console opens it by hand from the page card)."""
    d = _tdir(tenant)
    if not artifact_id or not d.is_dir():
        return None
    for sub in d.iterdir():
        m = _meta(tenant, sub.name) if sub.is_dir() else None
        if m and m.get("artifact_id") == artifact_id:
            return m
    return None


def read(tenant: str, did: str) -> dict[str, Any]:
    """What Hoola reads before it changes a diagram. An editable one: every cell + the shapes she has selected right now
    (with their labels) + its revision - and from now on Hoola may change it (until she edits it by hand again)."""
    from . import drawio_xml as X
    with _LOCK:
        m, desc = current(tenant, did)
        if m is None:
            return {"ok": False, "error": f"No diagram {did} here."}
        if m.get("engine") != "drawio":
            return {"ok": True, "diagram_id": did, "engine": m["engine"], "type": m["type"],
                    "description": desc[:40000], "editable_id": m.get("editable_id") or ""}
        m["ai_seen_rev"] = int(m.get("rev") or 0)
        _save_meta(tenant, m)
    cells = X.listing(desc)
    sel = [c for c in cells if c["id"] in set(m.get("selection") or [])]
    return {"ok": True, "diagram_id": did, "engine": "drawio", "rev": m.get("rev", 0), "cells": cells,
            "selected": sel, "last_change_by": m.get("last_by", ""),
            "said": ("She has SELECTED the shapes in 'selected' - when she says 'these' / 'this', change only those. "
                     if sel else "") + "Change it with action=change (ops id by id), never a full redraw of her work."}


def change(tenant: str, conv: str, did: str, ops: list[dict[str, Any]]) -> dict[str, Any]:
    """Hoola's change to an editable diagram, id by id (her other shapes stay exactly as she left them)."""
    from . import drawio_xml as X
    with _LOCK:
        m, desc = current(tenant, did)
        if m is None or m.get("engine") != "drawio":
            return {"ok": False, "error": "change is for an editable (draw.io) diagram; use action=update for the others."}
        g = _gate(m)
        if g:
            return {"ok": False, "diagram_id": did, "reason": "she changed it since you read it", "said": g}
        new, ids, probs = X.apply_ops(desc, ops)
        if probs:
            return {"ok": False, "diagram_id": did, "problems": probs, "reason": "the change does not fit the diagram",
                    "said": "Nothing changed. Fix the ops (ids from action=read) and send them again."}
    res = _try_drawio(m, _ddir(tenant, did) / f"change-{int(time.time())}", new)
    if not res["ok"]:
        return {"ok": False, "diagram_id": did, "problems": res["problems"], "reason": "could not draw the change"}
    with _LOCK:
        m, _desc = current(tenant, did)
        if _gate(m):                         # she edited while it was being drawn: hers wins, Hoola reads again
            return {"ok": False, "diagram_id": did, "reason": "she changed it meanwhile", "said": GATE}
        row = publish_drawio(tenant, conv, m, new, Path(res["html"]).read_text("utf-8"), note="Hoola's change")
        _save_desc(tenant, m, new)
        _after_ai_drawio(m, new, ids, ops=ops)
        _save_meta(tenant, m)
    out = _answer(m, res, row, [])
    out.update({"changed": ids, "said": ("Changed " + ", ".join(ids[:12]) + ". In her open editor it is outlined and "
                                         "one Ctrl+Z takes it back. The picture is attached - look at it.")})
    return out


def editable(tenant: str, did: str) -> dict[str, Any]:
    """An archify / diagram-design diagram she wants to change by hand: Hoola redraws it once as draw.io."""
    m, desc = current(tenant, did)
    if m is None:
        return {"ok": False, "error": f"No diagram {did} here."}
    if m.get("engine") == "drawio":
        from . import live as L
        return {"ok": True, "diagram_id": did, "editor": L.link(tenant, did), "said": "It is already editable."}
    if m.get("editable_id") and _meta(tenant, m["editable_id"]):
        from . import live as L
        return {"ok": True, "diagram_id": m["editable_id"], "editor": L.link(tenant, m["editable_id"]),
                "said": "It already has an editable copy."}
    return {"ok": True, "diagram_id": did, "engine": m["engine"], "description": desc[:40000],
            "said": ("Redraw THIS diagram as an editable draw.io diagram: read diagram action=guide type=drawio, then "
                     f"action=draw type=drawio from_id={did} with every part, label and connection of the description "
                     "below (same words, same grouping). The original stays as it is.")}
