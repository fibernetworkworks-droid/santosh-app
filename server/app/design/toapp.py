"""D7 bridge C - DESIGN -> APP STUDIO (docs/HOOLA_DESIGN_PLAN.md section 7 C).

She selects phone-size frames in Hoola Design and sends them to App Studio (the native app builder, app/appmaker/).
This module reads each frame the way the app builder can use it and hands it over THROUGH App Studio's own inputs:

  frames_to_screens(doc, ids)  -> per frame: its name, size class (phone / tablet / other), an ordered STRUCTURE
                                  (text with a role heading / body / label / button, inputs, buttons, images, icons,
                                  repeated siblings folded into "a list of N", top / bottom bars, boxes), its colours,
                                  fonts and spacing, and the prototype links between the selected frames.
  send(...)                    -> each frame is matched to one of App Studio's screen kinds (by its name, else by what
                                  is on it) and its structure becomes that screen's DESIGN in the app's plan - the same
                                  `plan.designs[<screen>]` line App Studio's own screen writer reads for every screen
                                  (`appmaker.service._screen_prompt`). A frame whose screen the app does not have yet is
                                  added as a new screen, exactly like App Studio's own "add a screen" change does.

What App Studio does with it, said plainly (read from appmaker/service.py, nothing of it is changed here):
  - App Studio's design is HTML screens drawn in its own kit by its screen writer; the native Android / iPhone build
    follows the design only after HER 'Approve design' tap (`service.approve`, "ONLY her tap", bound to the design's
    hash). Sending a design from the editor is NOT that tap: the bridge never calls `approve`, never marks a look
    approved, never starts a native build or a store step. Screens arrive in the "waiting for your OK" state.
  - An app that is past its plan + look (ready / approved / failed): the matched screens are drawn again at once by
    App Studio's own design run (`service._start(app, "design", only=..., extra=...)`, the path App Studio's change
    uses), with her frame as the owner's instruction. That run ends at "ready" and - App Studio's own rule - lifts an
    earlier approval until she approves the new screens.
  - An app before its look (planned / looks / stopped) or busy drawing: the designs are written into the plan only;
    App Studio draws them when it reaches those screens.
  - No app named: a NEW app plan through App Studio's own create path (`service.new`), then the designs as above.
  - The screen writer reads TEXT. The picture of each frame (rendered by the editor, PNG) is kept beside the app in
    `<app dir>/from_design/<screen>.png` with a manifest; App Studio's tabs do not show it (not built).
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request

MAX_FRAMES = 20
PICTURE_MAX = 3 * 1024 * 1024            # one frame's PNG (decoded)
PICTURES_MAX = 16 * 1024 * 1024          # all of them in one request (decoded)
BODY_MAX = 24 * 1024 * 1024              # the whole JSON request (base64 is ~4/3 of the bytes)
DESIGN_MAX = 1400                         # one screen's design line handed to App Studio
ELEMENTS_MAX = 120
TEXT_MAX = 120
_FRAMES = ("FRAME", "COMPONENT", "INSTANCE")
_SHAPES = ("RECT", "ELLIPSE", "POLYGON", "STAR", "VECTOR", "LINE")


class BridgeError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# ================================================================================ reading the document
def _nodes(doc: Any) -> dict[str, dict]:
    if isinstance(doc, str):
        doc = json.loads(doc)
    if isinstance(doc, dict) and isinstance(doc.get("nodes"), dict):
        return doc["nodes"]
    return doc if isinstance(doc, dict) else {}


class _Tree:
    def __init__(self, nodes: dict[str, dict]):
        self.n = nodes
        self.kids: dict[str, list[str]] = {}
        for nid, node in nodes.items():
            par = node.get("parent")
            if par is not None:
                self.kids.setdefault(par, []).append(nid)
        for lst in self.kids.values():
            lst.sort(key=lambda i: str(nodes[i].get("idx") or ""))

    def children(self, nid: str, inst: dict | None = None) -> list[tuple[str, dict]]:
        """(id, props) of the children; an INSTANCE shows its component's children with its overrides."""
        node = self.n.get(nid) or {}
        if node.get("type") == "INSTANCE" and node.get("comp") in self.n and not self.kids.get(nid):
            ov = node.get("ov") if isinstance(node.get("ov"), dict) else {}
            return [(k, {**self.n[k], **(ov.get(k) or {})}) for k in self.kids.get(node["comp"], [])]
        return [(k, self.n[k]) for k in self.kids.get(nid, [])]

    def top_frame(self, nid: str) -> str | None:
        """The top-level frame (child of a page) that holds `nid`."""
        cur, seen = nid, 0
        while cur in self.n and seen < 400:
            node = self.n[cur]
            par = node.get("parent")
            if par in self.n and self.n[par].get("type") == "PAGE":
                return cur
            cur, seen = par, seen + 1
        return None


def _num(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        return f if f == f and abs(f) < 1e9 else default
    except (TypeError, ValueError):
        return default


def _visible(p: dict) -> bool:
    return p.get("visible", True) is not False and _num(p.get("opacity", 1), 1) > 0.02


def _solid(p: dict) -> str:
    for paint in reversed(p.get("fills") or []):
        if isinstance(paint, dict) and paint.get("visible", True) is not False and paint.get("type") == "solid" \
                and re.fullmatch(r"#[0-9A-Fa-f]{6}", str(paint.get("color") or "")):
            return str(paint["color"]).upper()
    return ""


def _has_image(p: dict) -> bool:
    return any(isinstance(x, dict) and x.get("type") == "image" and x.get("visible", True) is not False
               for x in (p.get("fills") or []))


def _text(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()[:TEXT_MAX]


_RE_BUTTON = re.compile(r"\b(button|btn|cta)\b", re.I)
_RE_INPUT = re.compile(r"\b(input|field|text ?field|text ?box|search|search ?bar|email|password|phone|otp)\b", re.I)
_RE_IMAGE = re.compile(r"\b(image|img|photo|picture|pic|avatar|banner|thumbnail|thumb|cover|hero image|logo)\b", re.I)
_RE_TOPBAR = re.compile(r"\b(app ?bar|top ?bar|header|toolbar|nav ?bar|navbar|navigation|status ?bar)\b", re.I)
_RE_BOTTOM = re.compile(r"\b(tab ?bar|bottom ?(nav|bar|navigation|tabs?)|nav|navigation|tabs?|menu ?bar|dock)\b", re.I)
_RE_SECRET = re.compile(r"\b(password|passcode|pin|cvv|card number|upi pin)\b", re.I)


class _Reader:
    """One frame -> its structure."""

    def __init__(self, tree: _Tree, fid: str):
        self.t = tree
        self.fid = fid
        f = tree.n[fid]
        self.W = max(1.0, _num(f.get("w"), 100))
        self.H = max(1.0, _num(f.get("h"), 100))
        self.colours: Counter = Counter()
        self.text_colours: Counter = Counter()
        self.accents: Counter = Counter()
        self.fonts: Counter = Counter()
        self.sizes: Counter = Counter()
        self.weights: Counter = Counter()
        self.gaps: Counter = Counter()
        self.radii: Counter = Counter()
        self.pads: list = []
        self.texts: list[str] = []
        self.count = 0
        self.secret = False

    # --------------------------------------------------------------- what kind of thing a node is
    def _texts_in(self, nid: str, p: dict, depth: int = 0) -> list[str]:
        if p.get("type") == "TEXT":
            return [_text(p.get("chars"))] if _text(p.get("chars")) else []
        if depth > 5:
            return []
        out: list[str] = []
        for k, kp in self.t.children(nid):
            if _visible(kp):
                out.extend(self._texts_in(k, kp, depth + 1))
        return out

    def _kinds_in(self, nid: str, depth: int = 0) -> Counter:
        c: Counter = Counter()
        if depth > 5:
            return c
        for k, kp in self.t.children(nid):
            if not _visible(kp):
                continue
            c[kp.get("type")] += 1
            c.update(self._kinds_in(k, depth + 1))
        return c

    def _is_button(self, nid: str, p: dict) -> bool:
        if p.get("type") not in _FRAMES + ("GROUP",):
            return False
        texts = self._texts_in(nid, p)
        if _RE_BUTTON.search(str(p.get("name") or "")) and len(texts) <= 2:
            return True
        h, w = _num(p.get("h"), 100), _num(p.get("w"), 100)
        kinds = self._kinds_in(nid)
        others = sum(v for k, v in kinds.items() if k not in ("TEXT", "VECTOR", "STAR", "POLYGON", "ELLIPSE"))
        return (bool(_solid(p) or p.get("strokes")) and 20 <= h <= 72 and w <= self.W and len(texts) == 1
                and len(texts[0]) <= 32 and others == 0)

    def _is_input(self, p: dict) -> bool:
        return p.get("type") in _FRAMES + ("GROUP", "RECT") and bool(_RE_INPUT.search(str(p.get("name") or "")))

    def _is_image(self, nid: str, p: dict) -> bool:
        if p.get("type") == "TEXT":
            return False
        if _has_image(p):
            return True
        return (p.get("type") in ("RECT", "ELLIPSE") + _FRAMES and bool(_RE_IMAGE.search(str(p.get("name") or "")))
                and not self._texts_in(nid, p))

    def _role(self, nid: str, p: dict) -> str:
        if self._is_input(p):
            return "input"
        if self._is_button(nid, p):
            return "button"
        return "image" if self._is_image(nid, p) else "other"

    def _sig(self, nid: str, p: dict) -> tuple:
        kinds = self._kinds_in(nid) if p.get("type") in _FRAMES + ("GROUP", "SECTION") else Counter()
        return (p.get("type"), self._role(nid, p), round(_num(p.get("w"), 100) / 12), round(_num(p.get("h"), 100) / 12),
                tuple(sorted((k, min(v, 6)) for k, v in kinds.items())))

    # --------------------------------------------------------------- collecting the look
    def _look(self, p: dict, in_button: bool = False) -> None:
        c = _solid(p)
        if p.get("type") == "TEXT":
            self.fonts[str(p.get("font") or "Inter")] += 1
            self.sizes[int(round(_num(p.get("fontSize"), 16)))] += 1
            self.weights[int(_num(p.get("fontWeight"), 400))] += 1
            if c:
                self.text_colours[c] += 1
            return
        if c:
            area = _num(p.get("w"), 100) * _num(p.get("h"), 100)
            self.colours[c] += max(1, int(area // 100))
            if in_button:
                self.accents[c] += 1
        lay = p.get("layout") if isinstance(p.get("layout"), dict) else {}
        if lay.get("mode") in ("h", "v"):
            if _num(lay.get("gap")) > 0:
                self.gaps[int(round(_num(lay.get("gap"))))] += 1
            pad = lay.get("pad")
            if isinstance(pad, list) and any(_num(x) for x in pad) and len(self.pads) < 4:
                self.pads.append([int(round(_num(x))) for x in pad[:4]])
        rad = p.get("radius")
        if isinstance(rad, (int, float)) and rad > 0:
            self.radii[int(round(rad))] += 1

    # --------------------------------------------------------------- the walk
    def _order(self, nid: str, kids: list[tuple[str, dict]], p: dict) -> list[tuple[str, dict]]:
        lay = p.get("layout") if isinstance(p.get("layout"), dict) else {}
        if lay.get("mode") in ("h", "v"):
            return kids
        return sorted(kids, key=lambda kv: (round(_num(kv[1].get("y")) / 6), _num(kv[1].get("x"))))

    def _text_el(self, p: dict) -> dict:
        size, weight = _num(p.get("fontSize"), 16), _num(p.get("fontWeight"), 400)
        role = "heading" if size >= 20 or (size >= 17 and weight >= 600) else "label" if size <= 12 else "body"
        el = {"kind": "text", "role": role, "text": _text(p.get("chars")), "size": int(round(size))}
        if weight >= 600:
            el["bold"] = True
        return el

    def _el(self, nid: str, p: dict, depth: int, top: bool = False) -> list[dict]:
        if not _visible(p) or self.count >= ELEMENTS_MAX:
            return []
        self.count += 1
        typ = p.get("type")
        name = _text(p.get("name"))
        if _RE_SECRET.search(name):
            self.secret = True
        if typ == "TEXT":
            self._look(p)
            el = self._text_el(p)
            if el["text"]:
                self.texts.append(el["text"])
                if _RE_SECRET.search(el["text"]):
                    self.secret = True
                return [el]
            return []
        if top:
            bar = self._bar(nid, p)
            if bar:
                return [bar]
        if self._is_input(p):
            self._look(p)
            texts = self._texts_in(nid, p)
            self.texts.extend(texts)
            if _RE_SECRET.search(" ".join(texts)):
                self.secret = True
            el = {"kind": "input", "label": name, "placeholder": " / ".join(texts[:2])}
            if re.search(r"search", name + " " + " ".join(texts), re.I):
                el["search"] = True
            return [el]
        if self._is_button(nid, p):
            self._look(p, in_button=True)
            texts = self._texts_in(nid, p)
            self.texts.extend(texts)
            return [{"kind": "button", "text": texts[0] if texts else name}]
        if self._is_image(nid, p):
            self._look(p)
            return [{"kind": "image", "name": name, "w": int(_num(p.get("w"), 100)), "h": int(_num(p.get("h"), 100))}]
        if typ in _SHAPES:
            self._look(p)
            w, h = _num(p.get("w"), 100), _num(p.get("h"), 100)
            if typ in ("VECTOR", "STAR", "POLYGON") or (w <= 40 and h <= 40):
                return [{"kind": "icon", "name": name}]
            return []                                    # a plain shape is background / decoration
        # a container (frame, group, section, instance, component)
        self._look(p)
        if depth > 6:
            return []
        kids = self._order(nid, [kv for kv in self.t.children(nid) if _visible(kv[1])], p)
        inner = self._run(kids, depth + 1, False)
        if not inner:
            return []
        boxed = bool(_solid(p) or p.get("strokes") or p.get("effects")) and len(inner) >= 2
        if boxed:
            return [{"kind": "box", "name": name, "elements": inner}]
        return inner

    def _run(self, kids: list[tuple[str, dict]], depth: int, top: bool) -> list[dict]:
        """The children in order, with a run of 3+ siblings of the same shape folded into one list."""
        out: list[dict] = []
        i = 0
        sigs = [self._sig(k, kp) for k, kp in kids]
        while i < len(kids):
            j = i
            while j + 1 < len(kids) and sigs[j + 1] == sigs[i] and kids[i][1].get("type") != "TEXT" \
                    and sigs[i][1] not in ("input", "button"):          # a form's fields / a row of buttons stay one by one
                j += 1
            n = j - i + 1
            if n >= 3 and not (top and self._bar(*kids[i], collect=False)):
                first_id, first_p = kids[i]
                item = self._el(first_id, first_p, depth)
                if not item:                             # repeated plain shapes (dividers, dots): decoration
                    i = j + 1
                    continue
                for k, kp in kids[i + 1:j + 1]:          # the rest: their words and colours count, their shape does not
                    self.texts.extend(self._texts_in(k, kp))
                    self._look(kp)
                xs = [_num(kp.get("x")) for _, kp in kids[i:j + 1]]
                ys = [_num(kp.get("y")) for _, kp in kids[i:j + 1]]
                direction = "h" if (max(xs) - min(xs)) > (max(ys) - min(ys)) else "v"
                lst = {"kind": "list", "count": n, "direction": direction, "item": item[0] if len(item) == 1 else
                       {"kind": "box", "name": _text(first_p.get("name")), "elements": item}}
                out.append(lst)
                i = j + 1
                continue
            out.extend(self._el(kids[i][0], kids[i][1], depth, top))
            i += 1
        return out

    def _bar(self, nid: str, p: dict, collect: bool = True) -> dict | None:
        """A top or bottom bar: a direct child of the frame across (nearly) its whole width, at the top or bottom."""
        if p.get("type") not in _FRAMES + ("GROUP", "SECTION"):
            return None
        x, y = _num(p.get("x")), _num(p.get("y"))
        w, h = _num(p.get("w"), 100), _num(p.get("h"), 100)
        if w < 0.8 * self.W or h > 140 or h < 24:
            return None
        name = str(p.get("name") or "")
        kids = [kv for kv in self.t.children(nid) if _visible(kv[1])]
        if y + h >= self.H - 8 and (_RE_BOTTOM.search(name) or len(kids) >= 3):
            if not collect:
                return {"kind": "nav"}
            items = []
            for k, kp in sorted(kids, key=lambda kv: _num(kv[1].get("x"))):
                t = self._texts_in(k, kp)
                items.append(t[0] if t else _text(kp.get("name")))
            self.texts.extend(i for i in items if i)
            for k, kp in kids:
                self._look(kp)
            self._look(p)
            return {"kind": "nav", "where": "bottom", "count": len(items), "items": items[:6]}
        if y <= max(0.12 * self.H, 4) and (_RE_TOPBAR.search(name) or (bool(_solid(p)) and h <= 120 and x <= 4)):
            if not collect:
                return {"kind": "nav"}
            texts = self._texts_in(nid, p)
            self.texts.extend(texts)
            icons = self._kinds_in(nid)
            self._look(p)
            el = {"kind": "nav", "where": "top", "title": texts[0] if texts else _text(name), "items": texts[1:5]}
            if icons.get("VECTOR") or icons.get("INSTANCE"):
                el["icons"] = int(icons.get("VECTOR", 0) + icons.get("INSTANCE", 0))
            return el
        return None

    def read(self) -> dict:
        f = self.t.n[self.fid]
        bg = _solid(f)
        kids = self._order(self.fid, [kv for kv in self.t.children(self.fid) if _visible(kv[1])], f)
        self._look(f)
        elements = self._run(kids, 1, True)
        lefts = [int(round(_num(kp.get("x")))) for _, kp in kids if 0 < _num(kp.get("x")) < self.W / 3
                 and _num(kp.get("w"), 100) < self.W - 1]
        return {"elements": elements,
                "colors": {"background": bg, "text": [c for c, _ in self.text_colours.most_common(3)],
                           "accent": [c for c, _ in self.accents.most_common(3)],
                           "all": [c for c, _ in (self.colours + self.text_colours).most_common(8)]},
                "fonts": {"families": [f for f, _ in self.fonts.most_common(3)],
                          "sizes": sorted(s for s, _ in self.sizes.most_common(8)),
                          "weights": sorted(w for w, _ in self.weights.most_common(4))},
                "spacing": {"margin": Counter(lefts).most_common(1)[0][0] if lefts else 0,
                            "gaps": sorted(g for g, _ in self.gaps.most_common(4)),
                            "padding": self.pads[0] if self.pads else [],
                            "radius": sorted(r for r, _ in self.radii.most_common(3))},
                "texts": list(dict.fromkeys(t for t in self.texts if t))[:60],
                "secret_field": self.secret}


def size_class(w: float, h: float) -> tuple[str, str]:
    short, long_ = min(w, h), max(w, h)
    orient = "portrait" if h >= w else "landscape"
    if 300 <= short <= 500 and long_ <= 1100:
        return "phone", orient
    if 560 <= short <= 1100 and long_ <= 1400:
        return "tablet", orient
    return "other", orient


def frames_to_screens(doc: Any, frame_ids: list[str]) -> dict[str, Any]:
    """The selected frames as screens an app builder can read (see the module text). Unknown ids are an error."""
    tree = _Tree(_nodes(doc))
    ids = list(dict.fromkeys(str(x) for x in frame_ids or []))
    if not ids:
        raise BridgeError("Select one or more frames to send (each frame is one screen of the app).")
    if len(ids) > MAX_FRAMES:
        raise BridgeError(f"Send at most {MAX_FRAMES} frames at a time.")
    screens, warnings, links = [], [], []
    chosen = set(ids)
    for fid in ids:
        node = tree.n.get(fid)
        if node is None:
            raise BridgeError(f"There is no layer {fid} in this file (it may have been deleted).", 404)
        if node.get("type") not in _FRAMES:
            raise BridgeError(f"'{_text(node.get('name')) or fid}' is a {str(node.get('type')).lower()}, not a frame: "
                              "a screen is a frame.")
        w, h = _num(node.get("w"), 100), _num(node.get("h"), 100)
        cls, orient = size_class(w, h)
        if cls == "other":
            warnings.append(f"'{_text(node.get('name')) or fid}' is {int(w)} x {int(h)}: not a phone or tablet size. "
                            "App Studio designs for phones, so the screen will be laid out for a phone.")
        elif orient == "landscape":
            warnings.append(f"'{_text(node.get('name')) or fid}' is landscape; App Studio designs portrait screens first.")
        body = _Reader(tree, fid).read()
        screens.append({"frame": fid, "name": _text(node.get("name")) or "Screen", "w": int(w), "h": int(h),
                        "size_class": cls, "orientation": orient, **body})
    # prototype links: reactions on any layer of a selected frame
    by_frame = {s["frame"]: s for s in screens}
    outside = 0
    for fid in ids:
        stack = [fid]
        while stack:
            cur = stack.pop()
            p = tree.n.get(cur) or {}
            for rx in p.get("reactions") or []:
                if not isinstance(rx, dict):
                    continue
                act = rx.get("action")
                via = _text(p.get("chars")) if p.get("type") == "TEXT" else ""
                if not via and cur != fid:
                    t = _Reader(tree, fid)._texts_in(cur, p)
                    via = t[0] if t else _text(p.get("name"))
                if act == "back":
                    links.append({"from": fid, "to": "", "action": "back", "trigger": rx.get("trigger") or "click", "via": via})
                elif act in ("navigate", "swap", "overlay") and rx.get("to"):
                    target = str(rx["to"])
                    to_frame = target if target in chosen else tree.top_frame(target)
                    if to_frame in chosen and to_frame != fid:
                        links.append({"from": fid, "to": to_frame, "action": act, "trigger": rx.get("trigger") or "click",
                                      "via": via})
                    elif to_frame != fid:
                        outside += 1
            stack.extend(k for k in tree.kids.get(cur, []))
    if outside:
        warnings.append(f"{outside} prototype link(s) go to frames that were not sent; they are left out.")
    for s in screens:
        s["links"] = [{"to": ln["to"], "to_name": by_frame[ln["to"]]["name"] if ln["to"] else "", "action": ln["action"],
                       "via": ln["via"]} for ln in links if ln["from"] == s["frame"]]
    return {"screens": screens, "links": links, "warnings": warnings}


# ================================================================================ the words App Studio reads
def _el_words(el: dict, depth: int = 0) -> str:
    k = el.get("kind")
    if k == "text":
        return f"{el['role']} '{el['text']}'"
    if k == "input":
        return ("search field" if el.get("search") else "input") + (f" '{el['label'] or el['placeholder']}'" if (el.get("label") or el.get("placeholder")) else "")
    if k == "button":
        return f"button '{el['text']}'"
    if k == "image":
        return "image" + (f" ({el['name']})" if el.get("name") else "")
    if k == "icon":
        return "icon" + (f" {el['name']}" if el.get("name") else "")
    if k == "nav":
        if el["where"] == "bottom":
            return f"bottom navigation with {el['count']} tabs" + (f" ({', '.join(x for x in el['items'] if x)})" if any(el["items"]) else "")
        return "top bar" + (f" '{el['title']}'" if el.get("title") else "") + (f" with {', '.join(el['items'])}" if el.get("items") else "")
    if k == "list":
        item = el.get("item") or {}
        inner = _el_words(item, depth + 1) if depth < 2 else item.get("kind", "item")
        return f"a {'horizontal ' if el.get('direction') == 'h' else ''}list of {el['count']} ({inner})"
    if k == "box":
        if depth >= 2:
            return f"card '{el.get('name') or ''}'".replace(" ''", "")
        return "card [" + ", ".join(_el_words(x, depth + 1) for x in el.get("elements", [])[:8]) + "]"
    return k or ""


def design_text(screen: dict, file_name: str = "", names: dict[str, str] | None = None) -> str:
    """One screen in plain words, for App Studio's per-screen design line (capped)."""
    parts = [f"HER OWN DESIGN from Hoola Design (file '{_text(file_name)}', frame '{screen['name']}', "
             f"{screen['w']} x {screen['h']} {screen['size_class']}; layout data, follow its order): "]
    parts.append("; ".join(_el_words(e) for e in screen["elements"][:40]) + ".")
    c, f, sp = screen["colors"], screen["fonts"], screen["spacing"]
    look = []
    if c.get("background"):
        look.append(f"background {c['background']}")
    if c.get("text"):
        look.append("text " + "/".join(c["text"]))
    if c.get("accent"):
        look.append("buttons " + "/".join(c["accent"]))
    if look:
        parts.append(" Her colours: " + ", ".join(look) + ".")
    if f.get("families"):
        parts.append(f" Fonts: {', '.join(f['families'])} at {'/'.join(str(x) for x in f['sizes'][:6])}px.")
    sp_bits = []
    if sp.get("margin"):
        sp_bits.append(f"{sp['margin']}px side margin")
    if sp.get("gaps"):
        sp_bits.append("gaps " + "/".join(str(g) for g in sp["gaps"]) + "px")
    if sp.get("radius"):
        sp_bits.append("corners " + "/".join(str(r) for r in sp["radius"]) + "px")
    if sp_bits:
        parts.append(" Spacing: " + ", ".join(sp_bits) + ".")
    if screen.get("links"):
        lk = [f"'{ln['via'] or 'tap'}' -> {(names or {}).get(ln['to']) or ln['to_name'] or 'back'}" if ln["action"] != "back"
              else f"'{ln['via'] or 'back'}' goes back" for ln in screen["links"][:8]]
        parts.append(" Taps: " + "; ".join(lk) + ".")
    out = "".join(parts)
    return out if len(out) <= DESIGN_MAX else out[:DESIGN_MAX - 1].rstrip() + "…"


# ================================================================================ frame -> App Studio screen kind
_GENERIC = {"screen", "page", "frame", "view", "app", "the", "my", "a", "an", "of", "and", "new", "copy", "v", "mobile",
            "phone", "iphone", "android", "ios", "final", "draft", "ui", "design", "mockup", "1", "2", "3"}
_ALIASES = {
    "sign in": ["login"], "signin": ["login"], "log in": ["login"], "sign up": ["login"], "signup": ["login"],
    "register": ["login"], "otp": ["login"], "welcome": ["onboarding"], "intro": ["onboarding"],
    "walkthrough": ["onboarding"], "get started": ["onboarding"], "basket": ["cart"], "bag": ["cart"],
    "shopping cart": ["cart"], "account": ["profile"], "my account": ["profile"], "settings": ["profile"], "me": ["profile"],
    "explore": ["search"], "discover": ["search"], "product": ["product_detail"], "details": ["product_detail"],
    "detail": ["product_detail"], "item": ["product_detail"], "products": ["product_list"], "shop": ["product_list"],
    "listing": ["product_list"], "catalog": ["catalogue"], "inbox": ["notifications"], "alerts": ["notifications"],
    "messages": ["chat_list"], "chats": ["chat_list"], "chat": ["chat_thread"], "conversation": ["chat_thread"],
    "pay": ["payment"], "success": ["order_success"], "confirmation": ["order_success"], "thank you": ["order_success"],
    "tracking": ["order_track"], "track": ["order_track"], "my orders": ["orders"], "order history": ["orders"],
    "history": ["orders"], "favorites": ["wishlist"], "favourites": ["wishlist"], "saved": ["wishlist"],
    "book": ["slot_picker"], "booking": ["slot_picker", "booking_confirm"], "schedule": ["slot_picker"],
    "appointments": ["my_bookings"], "help": ["support"], "faq": ["support"], "contact": ["support", "store_info"],
    "dashboard": ["dashboard_kpi", "home"], "feed": ["home", "updates"], "main": ["home"], "landing": ["home"],
}


def _words(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in _GENERIC]


def match_screen(name: str, texts: list[str], in_plan: list[str]) -> tuple[str, str]:
    """(App Studio screen id, how it was matched) for a frame; ("", "") when nothing fits."""
    from ..appmaker import taxonomy as T
    plain = " ".join(_words(name))
    if not plain and not texts:
        return "", ""
    choose = lambda opts: next((o for o in opts if o in in_plan), next((o for o in opts if o in T.SCREENS), ""))  # noqa: E731
    if plain:
        sid = plain.replace(" ", "_")
        if sid in T.SCREENS:
            return sid, "name"
        hits = [k for k, v in T.SCREENS.items() if plain in (v["label"].lower(), str(v.get("hi") or "").lower())]
        hits += [x for x in _ALIASES.get(plain, []) if x in T.SCREENS and x not in hits]
        if hits:                                         # the app's own screen first, then the exact label
            return next((x for x in hits if x in in_plan), hits[0]), "name"
        for alias in sorted(_ALIASES, key=len, reverse=True):
            if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", plain) and choose(_ALIASES[alias]):
                return choose(_ALIASES[alias]), "name"
        mine = set(plain.split())
        best, score = "", 0.0
        for k, v in T.SCREENS.items():
            theirs = set(_words(k.replace("_", " ") + " " + v["label"]))
            if not theirs:
                continue
            s = len(mine & theirs) / len(mine | theirs) + (0.15 if k in in_plan else 0)
            if s > score:
                best, score = k, s
        if score >= 0.5:
            return best, "name"
    words = " ".join(texts).lower()
    for pat, opts in ((r"\b(otp|sign in|log in|login|verify|phone number)\b", ["login"]),
                      (r"\b(checkout|subtotal|place order)\b.*|\btotal\b.*\b(checkout|proceed)\b", ["cart"]),
                      (r"\b(log ?out|sign out|edit profile)\b", ["profile"]),
                      (r"\b(order placed|order confirmed|thank you)\b", ["order_success"])):
        if re.search(pat, words) and choose(opts):
            return choose(opts), "content"
    return "", ""


# ================================================================================ pictures
def read_pictures(raw: Any, frame_ids: list[str]) -> dict[str, bytes]:
    """{frame id: PNG bytes} from {frame id: base64 (or a data: URL)}; every one checked by content and size."""
    from . import assets
    if not raw:
        return {}
    if not isinstance(raw, dict):
        raise BridgeError("pictures is an object {frame id: PNG as base64}.")
    out, total = {}, 0
    for fid, b64 in raw.items():
        if fid not in frame_ids:
            raise BridgeError(f"A picture was sent for {str(fid)[:40]}, which is not one of the frames being sent.")
        text = str(b64 or "")
        if text.startswith("data:"):
            text = text.split(",", 1)[-1]
        if len(text) > PICTURE_MAX * 4 // 3 + 8:
            raise BridgeError(f"The picture of one frame is larger than {PICTURE_MAX // (1024 * 1024)} MB.", 413)
        try:
            data = base64.b64decode(text, validate=True)
        except (binascii.Error, ValueError):
            raise BridgeError("A picture is not valid base64.") from None
        if len(data) > PICTURE_MAX:
            raise BridgeError(f"The picture of one frame is larger than {PICTURE_MAX // (1024 * 1024)} MB.", 413)
        total += len(data)
        if total > PICTURES_MAX:
            raise BridgeError(f"The pictures together are larger than {PICTURES_MAX // (1024 * 1024)} MB.", 413)
        try:
            mime, _w, _h = assets.sniff(data)
        except assets.BadImage as e:
            raise BridgeError(f"A picture could not be read: {e}", 415) from None
        if mime != "image/png":
            raise BridgeError("Pictures are sent as PNG.", 415)
        out[str(fid)] = data
    return out


# ================================================================================ the hand-over
def _app_link(app_id: str) -> str:
    return f"/console/apps#/app/{app_id}"


def send(tenant: str, file: dict, doc: Any, frame_ids: list[str], app: str = "", brief: str = "",
         pictures: dict[str, bytes] | None = None, conv: str = "") -> dict[str, Any]:
    """Synchronous: read the frames, then hand them to App Studio through its own functions (module text)."""
    from ..appmaker import kit as K
    from ..appmaker import service as A
    from ..appmaker import taxonomy as T
    from ..site import guard
    read = frames_to_screens(doc, frame_ids)
    screens, warnings = read["screens"], list(read["warnings"])
    every = " ".join(" ".join(s["texts"]) + " " + s["name"] for s in screens)
    bad = guard.brief_problem(every + " " + (brief or ""))
    if bad:
        raise BridgeError(bad.replace("website", "app").replace("Website", "App"))
    if any(s["secret_field"] for s in screens):
        warnings.append("A password / PIN / card field is in the design: App Studio never builds those (sign-in is by "
                        "phone OTP), so that field will not be in the app.")
    created = False
    if app:
        try:
            v = A.get(tenant, app)
        except A.AppError:
            raise BridgeError("That app was not found in App Studio.", 404) from None
        if v.get("status") == "spec":
            raise BridgeError("That app is still a plan card; open it in App Studio first.", 409)
    else:
        words = (brief or "").strip() or f"{file.get('name') or ''} app"
        try:
            v = A.new(tenant, words, conv, name=str(file.get("name") or "")[:120])
        except A.AppError as e:
            raise BridgeError("App Studio asks: " + str(e) + " Say in a few words what the app is for, then send again.") from None
        created = True
    app_id = v["id"]
    row = A._load(app_id)
    plan = A._j(row.plan, {})
    in_plan = list(plan.get("screens", []))
    names = {s["frame"]: s["name"] for s in screens}
    done: dict[str, str] = {}
    results = []
    for s in screens:
        sid, how = match_screen(s["name"], s["texts"], in_plan)
        if sid in T.CODE_SCREENS:
            sid, how = "", ""
        res = {"frame": s["frame"], "name": s["name"], "size_class": s["size_class"], "screen": sid,
               "label": "", "matched_by": how, "structure": {k: s[k] for k in ("elements", "colors", "fonts", "spacing", "links")}}
        if not sid:
            res["state"] = "not_matched"
            warnings.append(f"'{s['name']}' is not one of App Studio's screen kinds, so it was kept as a proposal only. "
                            "Rename the frame to what the screen is (Login, Home, Cart, Profile ...) and send it again.")
        elif sid in done:
            res["state"], res["screen"] = "duplicate", ""
            warnings.append(f"'{s['name']}' and '{done[sid]}' both look like the {T.SCREENS[sid]['label']} screen; "
                            f"only '{done[sid]}' was used.")
        else:
            done[sid] = s["name"]
            res["added"] = sid not in plan.get("screens", [])
            if res["added"]:                         # App Studio's own "add a screen" change, the same three lines
                plan.setdefault("screens", []).append(sid)
                plan.setdefault("labels", {})[sid] = T.SCREENS[sid]["label"]
            plan.setdefault("designs", {})[sid] = design_text(s, file.get("name") or "", names)
            res["label"] = (plan.get("labels") or {}).get(sid) or T.SCREENS[sid]["label"]
        results.append(res)
    used = {r["screen"]: r for r in results if r["screen"] and r.get("state") is None}
    if not used:
        if created:
            A._save(app_id, plan=plan)
        raise BridgeError("None of the frames matched a screen App Studio can build. Name each frame after its screen "
                          "(Login, Home, Cart, Profile ...) and send again." + (" The new app plan was kept." if created else ""))
    status = row.status
    tokens = (A._j(row.look, {}) or {}).get("tokens")
    run = False
    if status in ("ready", "approved", "failed") and tokens:
        extra = {sid: ("OWNER'S DESIGN (she drew this screen herself in Hoola Design; follow its structure and order, keep "
                       "the app's chosen look and kit): " + plan["designs"][sid])[:1800] for sid in used}
        A._save(app_id, plan=plan, status="designing", conv=conv or row.conv)
        A._start(app_id, "design", only=list(used), note=f"From Hoola Design: {_text(file.get('name'))}"[:200], extra=extra)
        run = True
        state, say = "drawing", "App Studio is drawing these screens from your design now; they then wait for your OK."
        if status == "approved":
            warnings.append("This app's design was approved before. App Studio lifts that approval while the new screens "
                            "are drawn: approve the design again in App Studio when they are ready.")
    else:
        A._save(app_id, plan=plan)
        if status in ("designing", "checking"):
            state = "saved"
            say = ("App Studio is drawing screens right now. Your design is saved on these screens and is used the next time "
                   "they are drawn; send again when it is done to redraw them at once.")
        elif status == "stopped":
            state = "saved"
            say = "The app is paused in App Studio. Your design is saved on these screens; press Resume there to draw them."
        else:
            state = "waiting_plan"
            say = ("Your design is on these screens of the app plan. Approve the plan in App Studio and pick a look; every "
                   "screen is then drawn from your design and waits for your OK.")
    for r in used.values():
        r["state"] = state
    # pictures beside the app (App Studio's tabs do not show them; the manifest says what came from where)
    pics = pictures or {}
    keep = K.app_dir(tenant, app_id) / "from_design"
    keep.mkdir(parents=True, exist_ok=True)
    man_path = keep / "manifest.json"
    try:
        manifest = json.loads(man_path.read_text())
    except (OSError, ValueError):
        manifest = {}
    stamp = datetime.now(timezone.utc).isoformat()
    for sid, r in used.items():
        if r["frame"] in pics:
            (keep / f"{sid}.png").write_bytes(pics[r["frame"]])
        r["picture"] = (keep / f"{sid}.png").exists() and r["frame"] in pics
        manifest[sid] = {"file": file.get("id"), "file_name": file.get("name"), "frame": r["frame"], "frame_name": r["name"],
                         "picture": bool(r["picture"]), "at": stamp}
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    if not pics:
        warnings.append("No pictures came with this send (they come when she sends from the editor); App Studio reads the "
                        "structure either way.")
    after = A._load(app_id)
    return {"app": {"id": app_id, "number": after.number, "name": after.name, "status": after.status, "created": created},
            "screens": results, "links": read["links"], "url": _app_link(app_id), "warnings": warnings, "say": say,
            "redraw": run, "approved": False}


# ================================================================================ HTTP
def mount(r, current_tenant) -> None:
    """POST /api/design/files/{id}/to-app on the design router (key + switch already checked by the router)."""
    from . import store
    from .room import HUB, bg

    @r.post("/files/{file_id}/to-app")
    async def to_app(file_id: str, request: Request, tenant: str = Depends(current_tenant)):
        """{nodes: [frame ids], app?: App Studio app id / number, brief?: what the app is for (new app),
        pictures?: {frame id: PNG as base64}} -> {app, screens, url, warnings}. JSON only; the whole body is capped."""
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > BODY_MAX:
            raise HTTPException(413, f"The request is larger than {BODY_MAX // (1024 * 1024)} MB.")
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > BODY_MAX:
                raise HTTPException(413, f"The request is larger than {BODY_MAX // (1024 * 1024)} MB.")
            chunks.append(chunk)
        try:
            body = json.loads(b"".join(chunks) or b"{}")
        except ValueError:
            raise HTTPException(400, "Send JSON.") from None
        if not isinstance(body, dict):
            raise HTTPException(400, "Send a JSON object.")
        file = await bg(store.get_file, tenant, file_id)
        if file is None or file.get("trashed"):
            raise HTTPException(404, "File not found")
        got = await HUB.read(file_id, tenant)
        if got is None:
            raise HTTPException(404, "File not found")
        nodes = [str(x) for x in body.get("nodes") or [] if isinstance(x, (str, int))] if isinstance(body.get("nodes"), list) else []
        try:
            pics = read_pictures(body.get("pictures"), nodes)
            return await bg(send, tenant, file, got[1], nodes, str(body.get("app") or "").strip(),
                            str(body.get("brief") or "")[:600], pics, str(body.get("conversation_id") or ""))
        except BridgeError as e:
            raise HTTPException(e.status, str(e)) from None


def frames_by_name(doc: Any, refs: list[str]) -> list[str]:
    """Frame ids from ids or frame names (for the agent tool); none given = every phone / tablet size top-level frame."""
    tree = _Tree(_nodes(doc))
    tops = [k for k, n in tree.n.items() if n.get("type") in _FRAMES and (tree.n.get(n.get("parent")) or {}).get("type") == "PAGE"]
    if not refs:
        return [k for k in tops if size_class(_num(tree.n[k].get("w"), 100), _num(tree.n[k].get("h"), 100))[0] != "other"][:MAX_FRAMES]
    out = []
    for ref in refs:
        ref = str(ref).strip()
        if ref in tree.n:
            out.append(ref)
            continue
        hits = [k for k in tops if _text(tree.n[k].get("name")).lower() == ref.lower()]
        if len(hits) != 1:
            raise BridgeError(f"No single frame called '{ref[:60]}' in this file." if not hits else
                              f"More than one frame is called '{ref[:60]}': pass its id.")
        out.append(hits[0])
    return out
