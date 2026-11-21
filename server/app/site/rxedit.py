"""v0.999.76 D7 EDIT FOREVER, FOR FREE (docs/WEB_DESIGN_ENGINE_PLAN.md P9) on a website written in React (D4-D6).

Everything here is code: no model is called, so every edit costs Rs 0 (only a rewrite she asks for in the chat uses the
model, and that is the chat's own turn).

  sections()   every section of every page: its number, block, layout, background, the layouts / backgrounds it may take,
               and its WORDS with their place in the section (writer.texts_of) - the Studio shows them, the chat reads them
  words()      she clicked words in the preview and typed new ones: found by their text inside THAT section (exact, else
               the one place that contains them), kept as her edit (appengine/edits.py), the pages written again by code
  section()    another layout / background, leave a section out or bring it back - only what that section allows
  undo()       the last change of hers, put back (30 kept)
  design() / set_design()   the design panel: brand colour, light / dark, corners, spacing, motion, the two fonts - one
               change rewrites the design tokens (DESIGN.md) and every page follows; every colour pair checked first

After each change the app's debounced build runs (pre-rendered pages, the same as every build); the preview shows the
new version when it is built (~30 s). Her phone, address, hours and email are changed in Settings, never in a section."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

log = logging.getLogger("santosh.site")


class EditError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


def _site(tenant: str, site_id: str):
    from ..db import session
    from . import prototype as PT
    from . import service as S
    try:                                             # her site by id, number (S-0001) or name - only her own
        with session() as s:
            r = S._find(s, tenant, site_id)
            s.expunge(r)
    except S.SiteError as e:
        raise EditError(str(e), 404) from None
    link = PT.react_link(r)
    if not link.get("id"):
        raise EditError("This website is not written in React yet - build it from your prototype first.", 409)
    return r, link["id"], PT.pages_of(r), PT._j(r.facts, {})


def _ctx(r, pages, facts):
    from ..appengine import writer as W
    return W.Ctx(r.name or "", pages, facts, r.id, None)


def _state(tenant: str, ref: str, pages: list[dict[str, Any]]):
    from ..appengine import edits as ED
    design, custom, words = ED.merged(tenant, ref)
    custom = {**ED.custom_on_disk(tenant, ref, pages), **custom}
    return design, custom, words


def _rows(tenant: str, r, ref: str, pages, facts) -> list[dict[str, Any]]:
    from ..appengine import writer as W
    design, custom, words = _state(tenant, ref, pages)
    _, rows = W.plan_files(pages, _ctx(r, pages, facts), custom, design, None, words)
    return rows


def sections(tenant: str, site_id: str) -> dict[str, Any]:
    from ..appengine import edits as ED
    from ..appengine import service as AE
    r, ref, pages, facts = _site(tenant, site_id)
    rows = _rows(tenant, r, ref, pages, facts)
    e = ED.edits(tenant, ref)
    n: dict[str, int] = {}
    out = []
    for x in rows:
        page = x["page"]
        shown = bool(x.get("block"))
        if shown:
            n[page] = n.get(page, 0) + 1
        out.append({"sec": x.get("sec"), "page": page, "n": n.get(page, 0) if shown else None,
                    "type": x.get("type"), "block": x.get("block"), "variant": x.get("variant") or "",
                    "tone": x.get("tone") or "", "alts": x.get("alts") or [], "tones": x.get("tones") or [],
                    "texts": (x.get("texts") or [])[:40], "left_out": not shown, "why": x.get("why") or "",
                    "hers": x.get("sec") in (e.get("sections") or {}) or x.get("sec") in (e.get("words") or {})})
    app = AE._load(tenant, ref)
    return {"sections": out, "undo": len(e.get("undo") or []), "app": ref, "version": app.version,
            "building": bool(app.dirty)}


def _norm(s: str) -> str:
    return " ".join(str(s or "").split())


def _rewrite(tenant: str, r, ref: str, pages, facts) -> dict[str, Any]:
    """Write the pages again from her prototype + the design + her edits - code only - and start the build."""
    from .. import usage as U
    from ..appengine import service as AE
    from ..appengine import writer as W
    design, custom, words = _state(tenant, ref, pages)
    meter: dict[str, Any] = {}
    with U.run_meter(meter):
        st = W.write_app(tenant, ref, pages, name=r.name or "", facts=facts, model=None, seed=r.id, design=design,
                         reuse=custom, edits=words)
    if st["refused_left"]:
        raise EditError("That change could not be written: " + "; ".join(x["why"][:160] for x in st["refusals"][:2]), 422)
    AE.schedule_build(tenant, ref, delay=1.0)
    return {"calls": int(meter.get("calls") or 0), "inr": round(float(meter.get("usd") or 0) * U.usd_inr(), 2)}


def words(tenant: str, site_id: str, sec: str, old: str, new: str) -> dict[str, Any]:
    from ..appengine import edits as ED
    r, ref, pages, facts = _site(tenant, site_id)
    new = " ".join(str(new or "").split())
    if not new:
        raise EditError("Type the new words (to remove a whole section, use Leave out).")
    if len(new) > ED.MAX_WORDS:
        raise EditError(f"Keep it under {ED.MAX_WORDS} characters.")
    row = next((x for x in _rows(tenant, r, ref, pages, facts) if x.get("sec") == sec and x.get("block")), None)
    if not row:
        raise EditError("That section is not on the page.", 404)
    if row["block"] == "custom":
        raise EditError("This section was written specially for your site - ask in the chat to change its words.", 409)
    o = _norm(old)
    texts = row.get("texts") or []
    hit = next((t for t in texts if _norm(t["value"]) == o), None)
    value = new
    if not hit and len(o) >= 3:                      # the words she clicked are part of a longer text: the one place
        many = [t for t in texts if o in _norm(t["value"])]
        if len(many) == 1:
            hit = many[0]
            value = _norm(hit["value"]).replace(o, new, 1)
    if not hit:
        raise EditError("Those words are not text Hoola can change here (a phone, address or hours is changed in "
                        "Settings; a button's link in the chat).", 409)
    if _norm(hit["value"]) == _norm(value):
        return {"say": "Nothing changed.", "inr": 0.0, "calls": 0}
    ED.put_words(tenant, ref, sec, hit["path"], value, was=hit["value"])
    cost = _rewrite(tenant, r, ref, pages, facts)
    return {"say": "Changed. The page is being built again (about 30 seconds).", "sec": sec, "path": hit["path"],
            "value": value, **cost}


def section(tenant: str, site_id: str, sec: str, variant: str = "", tone: str = "", drop: bool | None = None) -> dict[str, Any]:
    from ..appengine import critic as C
    from ..appengine import edits as ED
    r, ref, pages, facts = _site(tenant, site_id)
    rows = _rows(tenant, r, ref, pages, facts)
    row = next((x for x in rows if x.get("sec") == sec), None)
    if not row:
        raise EditError("That section is not on the page.", 404)
    choice: dict[str, Any] = {}
    if drop is False:
        if row.get("block"):
            raise EditError("That section is already on the page.")
        her_drop = ((ED.edits(tenant, ref).get("sections") or {}).get(sec) or {}).get("drop")
        if not her_drop and "after the design review" not in (row.get("why") or ""):
            raise EditError("That section has nothing true to show yet (no number or fact was given for it).")
        choice["drop"] = False
    elif drop:
        if not row.get("block"):
            raise EditError("That section is already left out.")
        if row["block"] in C.NEVER_DROP:
            raise EditError("This section is needed on the page (the top, the contact or the sign-in).")
        page = sec.split(":", 1)[0]
        if len([x for x in rows if x["page"] == page and x.get("block")]) <= 2:
            raise EditError("A page keeps at least two sections.")
        choice["drop"] = True
    else:
        if not row.get("block"):
            raise EditError("Bring the section back first.")
        if variant:
            if variant not in (row.get("alts") or []):
                raise EditError("That layout does not suit this section's words.")
            choice["variant"] = variant
        if tone:
            if tone not in (row.get("tones") or []):
                raise EditError("That background is not offered for this section.")
            choice["tone"] = tone
        if not choice:
            raise EditError("Choose a layout or a background.")
    ED.put_section(tenant, ref, sec, choice)
    cost = _rewrite(tenant, r, ref, pages, facts)
    what = ("left out" if choice.get("drop") else "brought back" if drop is False else
            ", ".join(f"{k} {v}" for k, v in choice.items()))
    return {"say": f"Section {what}. The page is being built again (about 30 seconds).", **cost}


def undo(tenant: str, site_id: str) -> dict[str, Any]:
    from ..appengine import edits as ED
    r, ref, pages, facts = _site(tenant, site_id)
    got = ED.undo(tenant, ref)
    if not got:
        raise EditError("Nothing to undo.", 409)
    cost = _rewrite(tenant, r, ref, pages, facts)
    return {"say": f"Undone: {got['undone']}. The page is being built again.", **cost}


# ---------------------------------------------------------------- the design panel (tokens)
def design(tenant: str, site_id: str) -> dict[str, Any]:
    from ..appengine import genome as GN
    from ..appengine import service as AE
    r, ref, _, _ = _site(tenant, site_id)
    g = AE._genome(AE._load(tenant, ref))
    if not g:
        raise EditError("This website has no design system yet.", 409)
    fonts = [{"name": k, "role": list(v.get("role") or []), "cls": v.get("cls")} for k, v in GN.FONTS.items()
             if GN.font_files(k)]
    return {"design": GN.summary(g), "directions": [{"key": k, "label": v["label"]} for k, v in GN.DIRECTIONS.items()],
            "modes": list(GN.MODES), "densities": list(GN.DENSITY), "motions": list(GN.MOTION),
            "radius": [0, 32], "fonts": fonts}


def set_design(tenant: str, site_id: str, *, hue: float | None = None, colour: str = "", mode: str = "",
               radius: int | None = None, density: str = "", motion: str = "", display: str = "", text: str = "",
               direction: str = "") -> dict[str, Any]:
    """One change to her design tokens: merged into her genome, every colour pair checked, every page follows."""
    from ..appengine import genome as GN
    from ..appengine import service as AE
    from ..appengine import tokens as TK
    r, ref, _, _ = _site(tenant, site_id)
    g = AE._genome(AE._load(tenant, ref))
    if not g:
        raise EditError("This website has no design system yet.", 409)
    g = json.loads(json.dumps(g))
    if direction:
        if direction not in GN.DIRECTIONS:
            raise EditError("Unknown direction.")
        try:   # a new direction = a new genome in that direction that keeps her brand colour and mode
            res = AE.set_design(tenant, ref, direction=direction, mode=g["colour"]["mode"],
                                pin=g["colour"].get("pin") or GN.palette(g["colour"], g["colour"]["mode"])["primary"],
                                words=g["direction"].get("words") or "")
        except AE.AppEngineError as e:
            raise EditError(str(e), 422) from None
        return {"say": res["say"], "design": res["design"], "inr": 0.0, "calls": 0}
    if colour:
        if not TK.HEX.match(colour):
            raise EditError("A colour like #1f6feb.")
        g["colour"]["pin"] = colour.lower()
        g["colour"]["hue"] = round(GN.hex_oklch(colour)[2], 1)
    elif hue is not None:
        g["colour"]["hue"] = float(hue) % 360
        g["colour"]["pin"] = ""
    if mode:
        if mode not in GN.MODES:
            raise EditError("Light or dark.")
        g["colour"]["mode"] = mode
    if radius is not None:
        g["shape"]["radius"] = max(0, min(32, int(radius)))
    if density:
        if density not in GN.DENSITY:
            raise EditError("Unknown spacing.")
        g["density"] = density
    if motion:
        if motion not in GN.MOTION:
            raise EditError("Unknown motion.")
        g["motion"] = motion
    for role, fam in (("display", display), ("text", text)):
        if fam:
            if fam not in GN.FONTS or not GN.font_files(fam):
                raise EditError(f"That font is not one of Hoola's bundled fonts: {fam}")
            g["type"][role] = fam
    try:
        res = AE.set_design(tenant, ref, genes=g)
    except AE.AppEngineError as e:
        raise EditError(str(e), 422) from None
    return {"say": res["say"], "design": res["design"], "inr": 0.0, "calls": 0}


# ---------------------------------------------------------------- for the chat (a React site's sections, short)
def chat_block(tenant: str, site_id: str) -> str:
    """The chat agent's view of a React site: numbered sections with their words, and how to change them exactly."""
    try:
        got = sections(tenant, site_id)
    except EditError:
        return ""
    lines = []
    for s in got["sections"][:60]:
        if s["left_out"]:
            continue
        words = "; ".join(re.sub(r"\s+", " ", t["value"])[:70] for t in s["texts"][:4])
        lines.append(f"- {s['sec']} ({s['page']} section {s['n']}): {s['block']} {s['variant']}"
                     + (f", background {s['tone']}" if s["tone"] else "") + (f" - {words}" if words else ""))
    return ("THIS WEBSITE IS WRITTEN IN REACT (kit blocks + her words). Change it with EXACT edits, never a page rewrite: "
            "website action=rx_edit with sec + old (the words now) + new (her words), or sec + variant / tone / drop; "
            "action=rx_undo puts the last edit back. Her phone, address, hours and email are changed in Settings. "
            "Sections:\n" + "\n".join(lines))
