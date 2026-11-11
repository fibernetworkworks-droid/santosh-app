"""D7 bridge A - FIGMA IMPORT (docs/HOOLA_DESIGN_PLAN.md section 7 A).

No network anywhere: Figma is a fake behind httpx.MockTransport (figma.set_transport). The fixtures are written by
hand from Figma's documented REST shapes (GET /v1/files/:key?geometry=paths, /v1/files/:key/images, /v1/images/:key).
What is tested: the converter prop by prop (coordinates from relativeTransform incl. rotation, mirroring and Figma's
group-has-no-coordinate-space rule, auto layout, constraints, paints, effects, text runs, vectors normalised to their
box, boolean groups, masks, sections, components + instances with overrides, detached instances, prototype links,
caps); the job end to end through the real routes (token missing 409, 403 / 404 in plain words, 429 waited out,
pictures stored by content and referenced, a normal file that passes the document rules), tenant isolation, and that
the token never shows up in any answer, job record or log line."""
import io
import json
import logging
import math
import time

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.design import figma, figma_convert as FC
from app.design.ai import id_maker
from app.design.doc import APPLIED, ROOT, Doc, new_document

H = {"Authorization": "Bearer kd"}
TOKEN = "figd_" + "Q" * 30 + "zz9w"
KEY = "AbCdEfGhIjKlMnOp"
LINK = f"https://www.figma.com/design/{KEY}/My-App?node-id=0-1"


def solid(r, g, b, a=1.0, **kw):
    return {"type": "SOLID", "color": {"r": r, "g": g, "b": b, "a": a}, **kw}


def rt(e, f, a=1.0, b=0.0, c=0.0, d=1.0):
    """Figma relativeTransform [[a, c, e], [b, d, f]]."""
    return [[a, c, e], [b, d, f]]


def box(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def png(w=4, h=3, color=(200, 30, 30)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    return buf.getvalue()


# a rectangle turned 30 degrees counter-clockwise on screen (Figma's own rotation direction) and mirrored
COS, SIN = math.cos(math.radians(30)), math.sin(math.radians(30))


def figma_file():
    """A realistic file: one page with every feature of section 7A, a second page."""
    frame_abs = (100, 50)
    return {
        "name": "My App", "schemaVersion": 0, "version": "123",
        "styles": {"S:fill1": {"key": "k1", "name": "Brand / Blue", "styleType": "FILL"}},
        "components": {"2:1": {"key": "ck", "name": "Button", "description": "Main button"},
                       "99:1": {"key": "rk", "name": "Remote", "remote": True}},
        "document": {"id": "0:0", "type": "DOCUMENT", "name": "Document", "children": [
            {"id": "0:1", "type": "CANVAS", "name": "Home", "backgroundColor": {"r": 0.9, "g": 0.9, "b": 0.9, "a": 1},
             "flowStartingPoints": [{"nodeId": "1:2", "name": "Flow 1"}], "children": [
                {"id": "1:2", "type": "FRAME", "name": "Screen", "relativeTransform": rt(*frame_abs),
                 "size": {"x": 375, "y": 812}, "absoluteBoundingBox": box(100, 50, 375, 812),
                 "fills": [solid(1, 1, 1)], "styles": {"fill": "S:fill1"}, "clipsContent": True, "cornerRadius": 24,
                 "layoutMode": "VERTICAL", "itemSpacing": 12, "paddingTop": 16, "paddingRight": 20, "paddingBottom": 24,
                 "paddingLeft": 8, "primaryAxisAlignItems": "MIN", "counterAxisAlignItems": "CENTER",
                 "layoutSizingHorizontal": "FIXED", "layoutSizingVertical": "HUG", "overflowDirection": "VERTICAL_SCROLLING",
                 "effects": [{"type": "DROP_SHADOW", "color": {"r": 0, "g": 0, "b": 0, "a": 0.25}, "offset": {"x": 0, "y": 4},
                              "radius": 12, "spread": 2, "visible": True, "blendMode": "NORMAL"}],
                 "layoutGrids": [{"pattern": "COLUMNS", "sectionSize": 10, "visible": True, "color": {"r": 1, "g": 0, "b": 0, "a": 0.1},
                                  "alignment": "STRETCH", "gutterSize": 16, "offset": 8, "count": 4}],
                 "exportSettings": [{"suffix": "@2x", "format": "PNG", "constraint": {"type": "SCALE", "value": 2}}],
                 "children": [
                    {"id": "1:3", "type": "FRAME", "name": "Row", "relativeTransform": rt(8, 16), "size": {"x": 347, "y": 40},
                     "absoluteBoundingBox": box(108, 66, 347, 40), "fills": [], "clipsContent": False,
                     "layoutMode": "HORIZONTAL", "itemSpacing": 8, "paddingTop": 4, "paddingRight": 4, "paddingBottom": 4,
                     "paddingLeft": 4, "primaryAxisAlignItems": "SPACE_BETWEEN", "counterAxisAlignItems": "MIN",
                     "layoutSizingHorizontal": "FILL", "layoutSizingVertical": "HUG",
                     "interactions": [{"trigger": {"type": "ON_CLICK"}, "actions": [
                         {"type": "NODE", "destinationId": "4:2", "navigation": "NAVIGATE",
                          "transition": {"type": "DISSOLVE", "duration": 0.3, "easing": {"type": "EASE_OUT"}}}]}],
                     "children": [
                        {"id": "1:4", "type": "RECTANGLE", "name": "Chip", "relativeTransform": rt(4, 4), "size": {"x": 60, "y": 32},
                         "absoluteBoundingBox": box(112, 70, 60, 32), "layoutSizingHorizontal": "FIXED", "layoutSizingVertical": "FILL",
                         "fills": [{"type": "GRADIENT_LINEAR", "gradientHandlePositions": [{"x": 0, "y": 0}, {"x": 1, "y": 1}, {"x": 0, "y": 1}],
                                    "gradientStops": [{"position": 1, "color": {"r": 0, "g": 0, "b": 1, "a": 0.5}},
                                                      {"position": 0, "color": {"r": 1, "g": 0, "b": 0, "a": 1}}]}]},
                        {"id": "1:5", "type": "TEXT", "name": "Label", "relativeTransform": rt(72, 4), "size": {"x": 200, "y": 40},
                         "absoluteBoundingBox": box(180, 70, 200, 40), "layoutSizingHorizontal": "FILL", "layoutSizingVertical": "HUG",
                         "fills": [solid(0.1, 0.1, 0.1)], "characters": "Hello\nWorld",
                         "style": {"fontFamily": "Inter", "fontPostScriptName": "Inter-Medium", "fontWeight": 500, "fontSize": 14,
                                   "letterSpacing": 0.5, "lineHeightPx": 20, "lineHeightUnit": "PIXELS",
                                   "textAlignHorizontal": "CENTER", "textAlignVertical": "CENTER", "textAutoResize": "HEIGHT",
                                   "textCase": "UPPER", "textDecoration": "UNDERLINE"},
                         "characterStyleOverrides": [2, 2, 0, 0, 0, 0, 1, 1, 1, 1, 1],
                         "styleOverrideTable": {"1": {"fontWeight": 700, "fills": [solid(1, 0, 0)]},
                                                "2": {"italic": True, "fontSize": 18, "lineHeightUnit": "FONT_SIZE_%",
                                                      "lineHeightPercentFontSize": 150}}},
                     ]},
                    {"id": "1:6", "type": "RECTANGLE", "name": "Turned", "layoutPositioning": "ABSOLUTE",
                     "constraints": {"vertical": "BOTTOM", "horizontal": "RIGHT"},
                     "relativeTransform": [[-COS, SIN, 200], [SIN, COS, 300]], "size": {"x": 100, "y": 50},
                     "rectangleCornerRadii": [4, 8, 12, 16], "fills": [solid(0, 1, 0)],
                     "strokes": [solid(0, 0, 0)], "strokeWeight": 2, "strokeAlign": "INSIDE", "strokeDashes": [4, 2],
                     "strokeCap": "ROUND", "strokeJoin": "BEVEL"},
                    {"id": "1:7", "type": "RECTANGLE", "name": "Photo", "relativeTransform": rt(20, 700), "size": {"x": 80, "y": 60},
                     "fills": [{"type": "IMAGE", "imageRef": "img1", "scaleMode": "FIT", "opacity": 0.8}]},
                    {"id": "1:8", "type": "VECTOR", "name": "Arrow", "relativeTransform": rt(200, 400), "size": {"x": 80, "y": 80},
                     "fills": [solid(0, 0, 0)], "fillGeometry": [{"path": "M10 20L60 20L35 70Z", "windingRule": "EVENODD"}],
                     "strokeGeometry": []},
                    {"id": "1:9", "type": "BOOLEAN_OPERATION", "name": "Cut", "booleanOperation": "SUBTRACT",
                     "relativeTransform": rt(10, 500), "size": {"x": 100, "y": 100}, "absoluteBoundingBox": box(110, 550, 100, 100),
                     "fills": [solid(1, 0.5, 0)], "fillGeometry": [{"path": "M0 0L100 0L100 100L0 100Z", "windingRule": "NONZERO"}],
                     "children": [
                        {"id": "1:10", "type": "RECTANGLE", "name": "A", "relativeTransform": rt(10, 500), "size": {"x": 100, "y": 100},
                         "absoluteBoundingBox": box(110, 550, 100, 100), "fills": [solid(0, 0, 0)]},
                        {"id": "1:11", "type": "RECTANGLE", "name": "B", "relativeTransform": rt(40, 530), "size": {"x": 40, "y": 40},
                         "absoluteBoundingBox": box(140, 580, 40, 40), "fills": [solid(0, 0, 0)]},
                     ]},
                    {"id": "1:20", "type": "GROUP", "name": "Masked", "relativeTransform": rt(300, 600), "size": {"x": 60, "y": 60},
                     "absoluteBoundingBox": box(400, 650, 60, 60), "fills": [], "children": [
                        # this export writes the children relative to the GROUP itself: the bounding box decides
                        {"id": "1:21", "type": "RECTANGLE", "name": "Mask", "isMask": True, "relativeTransform": rt(0, 0),
                         "size": {"x": 50, "y": 50}, "absoluteBoundingBox": box(400, 650, 50, 50), "fills": [solid(0, 0, 0)]},
                        {"id": "1:22", "type": "ELLIPSE", "name": "Dot", "relativeTransform": rt(10, 10), "size": {"x": 50, "y": 50},
                         "absoluteBoundingBox": box(410, 660, 50, 50), "fills": [solid(0, 0, 1)]},
                     ]},
                 ]},
                {"id": "2:1", "type": "COMPONENT", "name": "Button", "description": "Main button",
                 "relativeTransform": rt(600, 50), "size": {"x": 120, "y": 40}, "fills": [solid(0, 0, 1)], "cornerRadius": 8,
                 "clipsContent": True,
                 "componentPropertyDefinitions": {"Label#1:0": {"type": "TEXT", "defaultValue": "Buy"}},
                 "children": [
                    {"id": "2:2", "type": "TEXT", "name": "Title", "relativeTransform": rt(10, 10), "size": {"x": 100, "y": 20},
                     "fills": [solid(1, 1, 1)], "characters": "Buy", "componentPropertyReferences": {"characters": "Label#1:0"},
                     "style": {"fontFamily": "Inter", "fontWeight": 600, "fontSize": 14, "lineHeightUnit": "INTRINSIC_%",
                               "lineHeightPx": 16.9, "textAutoResize": "NONE", "textAlignHorizontal": "LEFT", "textAlignVertical": "TOP"}},
                 ]},
                {"id": "3:1", "type": "INSTANCE", "name": "Button", "componentId": "2:1", "opacity": 0.5,
                 "relativeTransform": rt(600, 200), "size": {"x": 120, "y": 40}, "fills": [solid(0, 0, 1)], "cornerRadius": 8,
                 "clipsContent": True, "overrides": [{"id": "I3:1;2:2", "overriddenFields": ["characters"]}],
                 "children": [
                    {"id": "I3:1;2:2", "type": "TEXT", "name": "Title", "relativeTransform": rt(10, 10), "size": {"x": 100, "y": 20},
                     "fills": [solid(1, 1, 1)], "characters": "Sell",
                     "style": {"fontFamily": "Inter", "fontWeight": 600, "fontSize": 14, "lineHeightUnit": "INTRINSIC_%",
                               "lineHeightPx": 16.9, "textAutoResize": "NONE", "textAlignHorizontal": "LEFT", "textAlignVertical": "TOP"}},
                 ]},
                {"id": "3:5", "type": "INSTANCE", "name": "Remote thing", "componentId": "99:1", "relativeTransform": rt(600, 300),
                 "size": {"x": 50, "y": 50}, "fills": [], "clipsContent": True, "children": [
                    {"id": "I3:5;99:2", "type": "RECTANGLE", "name": "Inner", "relativeTransform": rt(5, 5), "size": {"x": 40, "y": 40},
                     "fills": [solid(0.5, 0.5, 0.5)]}]},
                {"id": "4:1", "type": "SECTION", "name": "Flows", "relativeTransform": rt(0, 1000), "size": {"x": 400, "y": 300},
                 "fills": [solid(0.93, 0.93, 0.93)], "children": [
                    {"id": "4:2", "type": "FRAME", "name": "Next", "relativeTransform": rt(20, 20), "size": {"x": 100, "y": 100},
                     "fills": [solid(1, 1, 1)], "clipsContent": True, "children": []}]},
                {"id": "5:1", "type": "STICKY", "name": "Note", "relativeTransform": rt(900, 900), "size": {"x": 200, "y": 200},
                 "absoluteBoundingBox": box(900, 900, 200, 200), "characters": "remember"},
                {"id": "6:1", "type": "SLICE", "name": "Export me", "relativeTransform": rt(0, 0), "size": {"x": 10, "y": 10}},
            ]},
            {"id": "0:2", "type": "CANVAS", "name": "Second", "backgroundColor": {"r": 0, "g": 0, "b": 0, "a": 1}, "children": []},
        ]},
    }


def convert(doc=None, cap=200_000):
    return FC.Converter(doc or figma_file(), id_maker(7), cap).run()


def by_name(ops):
    return {o["p"].get("name"): o for o in ops if "name" in o["p"]}


def check_matrix(p, abs_m, parent_m=FC.IDENT, w=None, h=None):
    """The props drawn by Hoola's own nodeMatrix land exactly on Figma's matrix."""
    w = p["w"] if w is None else w
    h = p["h"] if h is None else h
    local = FC.node_matrix(p.get("x", 0), p.get("y", 0), w, h, p.get("rot", 0), p.get("flipH", False), p.get("flipV", False))
    got = FC.mul(parent_m, local)
    assert all(abs(a - b) < 1e-3 for a, b in zip(got, abs_m)), (got, abs_m)


# ==================================================================================== the converter
def test_decompose_matches_hoola_nodematrix_for_rotation_and_mirroring():
    import random
    rnd = random.Random(7)
    for _ in range(200):
        rot, flip = rnd.uniform(-179, 180), rnd.random() < 0.5
        w, h, x, y = rnd.uniform(1, 300), rnd.uniform(1, 300), rnd.uniform(-500, 500), rnd.uniform(-500, 500)
        m = FC.node_matrix(x, y, w, h, rot, flip, rnd.random() < 0.3)
        geo, odd = FC.decompose(m, w, h)
        assert not odd
        check_matrix({**geo, "w": w, "h": h}, m)
    # Figma's own convention: rotation 30 = counter-clockwise on screen = Hoola -30 (Hoola turns clockwise)
    m = FC.from_figma([[COS, SIN, 0], [-SIN, COS, 0]])
    geo, _ = FC.decompose(m, 100, 50)
    assert geo["rot"] == pytest.approx(-30)
    cx, cy = COS * 50 + SIN * 25, -SIN * 50 + COS * 25          # the box centre, worked out by hand
    assert geo["x"] == pytest.approx(cx - 50, abs=1e-4) and geo["y"] == pytest.approx(cy - 25, abs=1e-4)
    # a plain horizontal mirror keeps the box where it is: Figma's origin is then the RIGHT edge
    geo, _ = FC.decompose(FC.from_figma([[-1, 0, 200], [0, 1, 10]]), 80, 30)
    assert geo == {"x": 120, "y": 10, "flipH": True}


def test_pages_frames_auto_layout_and_children_order():
    conv = convert()
    ops = conv.finish({"img1": "a" * 64}, {"5:1": "b" * 64})
    n = by_name(ops)
    page = ops[0]
    assert page["id"] == "0:1" and page["p"] == {"name": "Home", "idx": page["p"]["idx"], "bg": "#E6E6E6"}
    second = n["Second"]["p"]
    assert second["type"] == "PAGE" and second["parent"] == ROOT and second["bg"] == "#000000"
    assert page["p"]["idx"] < second["idx"]
    s = n["Screen"]
    assert s["p"]["parent"] == "0:1" and s["id"].startswith("7:")
    want = {"type": "FRAME", "x": 100, "y": 50, "w": 375, "h": 812, "radius": 24, "clip": True, "sizeV": "hug",
            "scroll": "v", "protoStart": True, "flowName": "Flow 1", "fillStyle": "fs_S_fill1",
            "fills": [{"type": "solid", "color": "#FFFFFF", "opacity": 1, "visible": True}],
            "layout": {"mode": "v", "gap": 12, "pad": [16, 20, 24, 8], "alignMain": "start", "alignCross": "center", "wrap": False},
            "effects": [{"type": "drop", "x": 0, "y": 4, "blur": 12, "spread": 2, "color": "#000000", "opacity": 0.25, "visible": True}],
            "grids": [{"type": "columns", "size": 10, "count": 4, "gutter": 16, "margin": 8, "align": "stretch", "color": "#FF0000",
                       "opacity": 0.1, "visible": True}],
            "exports": [{"fmt": "png", "scale": 2, "suffix": "@2x"}]}
    for k, v in want.items():
        assert s["p"][k] == v, k
    row = n["Row"]["p"]
    assert (row["x"], row["y"], row["w"], row["h"]) == (8, 16, 347, 40)
    assert row["sizeH"] == "fill" and row["sizeV"] == "hug" and row["clip"] is False and "fills" not in row
    assert row["layout"] == {"mode": "h", "gap": 8, "pad": [4, 4, 4, 4], "alignMain": "between", "alignCross": "start", "wrap": False}
    chip = n["Chip"]["p"]
    assert chip["parent"] == n["Row"]["id"] and chip["sizeV"] == "fill" and "sizeH" not in chip
    assert chip["fills"] == [{"type": "linear", "stops": [{"pos": 0, "color": "#FF0000", "opacity": 1},
                                                          {"pos": 1, "color": "#0000FF", "opacity": 0.5}],
                              "from": [0, 0], "to": [1, 1], "opacity": 1}]
    # first child in Figma = bottom = the lowest fractional index
    kids = [o for o in ops if o["p"].get("parent") == n["Screen"]["id"]]
    assert [o["p"]["name"] for o in sorted(kids, key=lambda o: o["p"]["idx"])] == ["Row", "Turned", "Photo", "Arrow", "Cut", "Masked"]
    # a frame of the root style is registered on the root, with its value
    root = next(o for o in ops if o["id"] == ROOT)
    assert root["p"]["styles"] == {"fs_S_fill1": {"kind": "fill", "name": "Brand / Blue",
                                                  "value": [{"type": "solid", "color": "#FFFFFF", "opacity": 1, "visible": True}]}}


def test_rotated_mirrored_rectangle_corners_strokes_constraints():
    n = by_name(convert().finish({}, {}))
    p = n["Turned"]["p"]
    assert p["flipH"] is True and p["w"] == 100 and p["h"] == 50
    check_matrix(p, FC.from_figma([[-COS, SIN, 200], [SIN, COS, 300]]))
    assert p["radius"] == [4, 8, 12, 16]
    assert p["cons"] == {"h": "right", "v": "bottom"} and p["layoutPos"] == "absolute"
    assert p["strokes"] == [{"type": "solid", "color": "#000000", "opacity": 1, "visible": True}]
    assert (p["strokeWeight"], p["strokeAlign"], p["strokeCap"], p["strokeJoin"], p["dash"]) == (2, "inside", "round", "bevel", [4, 2])


def test_text_style_two_runs_and_a_newline():
    p = by_name(convert().finish({}, {}))["Label"]["p"]
    assert p["chars"] == "Hello\nWorld"
    want = {"type": "TEXT", "font": "Inter", "fontSize": 14, "fontWeight": 500, "letterSpacing": 0.5, "lineHeight": 20,
            "align": "center", "alignV": "middle", "textCase": "upper", "decoration": "underline", "autoResize": "h",
            "sizeH": "fill", "fills": [{"type": "solid", "color": "#1A1A1A", "opacity": 1, "visible": True}]}
    for k, v in want.items():
        assert p[k] == v, k
    assert "sizeV" not in p
    assert p["runs"] == [{"s": 0, "e": 2, "fontSize": 18, "italic": True, "lineHeight": 27},
                         {"s": 6, "e": 11, "fontWeight": 700,
                          "fills": [{"type": "solid", "color": "#FF0000", "opacity": 1, "visible": True}]}]
    auto = by_name(convert().finish({}, {}))["Title"]["p"]
    assert auto["lineHeight"] == "auto" and auto["autoResize"] == "none" and auto["fontWeight"] == 600


def test_vector_is_normalised_to_its_box_and_images_are_referenced():
    n = by_name(convert().finish({"img1": "a" * 64}, {"5:1": "b" * 64}))
    v = n["Arrow"]["p"]
    assert v["type"] == "VECTOR" and v["path"] == "M0 0 L50 0 L25 50 Z" and v["fillRule"] == "evenodd"
    assert (v["x"], v["y"], v["w"], v["h"]) == (210, 420, 50, 50)
    img = n["Photo"]["p"]
    assert img["fills"] == [{"type": "image", "hash": "a" * 64, "mode": "fit", "opacity": 0.8}]
    note = n["Note"]["p"]
    assert note["type"] == "RECT" and note["fills"][0]["hash"] == "b" * 64 and (note["x"], note["y"]) == (900, 900)
    # a picture that could not be stored: the paint goes (counted); a fallback layer without its picture goes whole
    conv = convert()
    n2 = by_name(conv.finish({}, {}))
    assert "fills" not in n2["Photo"]["p"] and "Note" not in n2
    texts = {w["text"] for w in conv.warnings()}
    assert "Image fills whose picture could not be downloaded (not imported)" in texts
    assert "Layers Figma could not draw a picture of (not imported)" in texts


def test_boolean_mask_group_coordinates_and_sections():
    n = by_name(convert().finish({}, {}))
    cut = n["Cut"]["p"]
    assert cut["type"] == "GROUP" and cut["bool"] == "subtract" and (cut["x"], cut["y"], cut["w"], cut["h"]) == (10, 500, 100, 100)
    assert cut["fills"][0]["color"] == "#FF8000"
    a, b = n["A"]["p"], n["B"]["p"]
    assert a["parent"] == n["Cut"]["id"] and (a["x"], a["y"]) == (0, 0) and (b["x"], b["y"]) == (30, 30)
    g = n["Masked"]["p"]
    assert g["type"] == "GROUP" and "bool" not in g and "fills" not in g and (g["x"], g["y"]) == (300, 600)
    mask, dot = n["Mask"]["p"], n["Dot"]["p"]
    assert mask["mask"] is True and (mask["x"], mask["y"]) == (0, 0)
    assert dot["type"] == "ELLIPSE" and (dot["x"], dot["y"]) == (10, 10)      # read relative to the group: the box agreed
    sec, nxt = n["Flows"]["p"], n["Next"]["p"]
    assert sec["type"] == "SECTION" and (sec["x"], sec["y"]) == (0, 1000) and sec["fills"][0]["color"] == "#EDEDED"
    assert nxt["parent"] == n["Flows"]["id"] and (nxt["x"], nxt["y"]) == (20, 20)


def test_components_instances_overrides_detached_and_prototype():
    ops = convert().finish({}, {})
    n = by_name(ops)
    comps = [o for o in ops if o["p"].get("type") == "COMPONENT"]
    assert len(comps) == 1
    comp, title = comps[0], next(o for o in ops if o["p"].get("name") == "Title" and o["p"]["parent"] == comps[0]["id"])
    assert comp["p"]["desc"] == "Main button"
    assert comp["p"]["cprops"] == [{"id": "Label_1_0", "name": "Label", "type": "text", "target": title["id"], "def": "Buy"}]
    inst = next(o for o in ops if o["p"].get("type") == "INSTANCE")
    ip = inst["p"]
    assert ip["comp"] == comp["id"] and ip["opacity"] == 0.5 and (ip["x"], ip["y"]) == (600, 200)
    assert "fills" not in ip and "radius" not in ip and "clip" not in ip          # the same as the component: not repeated
    assert ip["ov"] == {title["id"]: {"chars": "Sell"}}
    assert not any(o["p"].get("parent") == inst["id"] for o in ops)            # an instance has no layers of its own
    remote = n["Remote thing"]
    assert remote["p"]["type"] == "FRAME" and n["Inner"]["p"]["parent"] == remote["id"]
    assert n["Row"]["p"]["reactions"] == [{"trigger": "click", "action": "navigate", "to": n["Next"]["id"],
                                           "anim": {"type": "dissolve", "dir": "left", "dur": 300, "ease": "out"}}]


def test_every_unmapped_thing_is_named_in_the_warnings():
    conv = convert()
    conv.finish({}, {})
    texts = {w["text"]: w["count"] for w in conv.warnings()}
    assert texts["Instances of a component that is not in this file (kept as frames, detached)"] == 1
    assert texts["Sticky layers (no Hoola equivalent: kept as Figma's picture of them)"] == 1
    assert texts["Export slices (not imported: Hoola keeps export settings on layers instead)"] == 1


def test_polygon_star_partial_ellipse_and_open_stroke():
    def shape(t, segs_pts, **kw):
        d = "M" + " L".join(f"{x:.4f} {y:.4f}" for x, y in segs_pts) + " Z"
        return {"id": kw.pop("id"), "type": t, "name": kw.pop("name"), "relativeTransform": rt(0, 0), "size": {"x": 90, "y": 60},
                "fills": [solid(0, 0, 0)], "fillGeometry": [{"path": d, "windingRule": "NONZERO"}], **kw}
    hexagon = [(x * 90, y * 60) for x, y in FC.poly_points(6, 1, False)]
    star = [(x * 90, y * 60) for x, y in FC.poly_points(5, 0.38, True)]
    doc = {"name": "S", "document": {"id": "0:0", "type": "DOCUMENT", "children": [{"id": "0:1", "type": "CANVAS", "name": "P", "children": [
        shape("REGULAR_POLYGON", hexagon, id="1:1", name="Hex"),
        shape("STAR", star, id="1:2", name="Star"),
        shape("REGULAR_POLYGON", [(0, 0), (90, 10), (40, 60)], id="1:3", name="Odd"),
        {"id": "1:4", "type": "ELLIPSE", "name": "Arc", "relativeTransform": rt(0, 0), "size": {"x": 40, "y": 40},
         "arcData": {"startingAngle": 0, "endingAngle": 3.14159, "innerRadius": 0},
         "fillGeometry": [{"path": "M40 20C40 31.046 31.046 40 20 40C8.954 40 0 31.046 0 20Z", "windingRule": "NONZERO"}]},
        {"id": "1:5", "type": "VECTOR", "name": "Pen", "relativeTransform": rt(5, 5), "size": {"x": 10, "y": 2}, "fills": [],
         "strokes": [solid(1, 0, 0)], "strokeWeight": 2, "fillGeometry": [],
         "strokeGeometry": [{"path": "M0 0L10 0L10 2L0 2Z", "windingRule": "NONZERO"}]},
        {"id": "1:6", "type": "LINE", "name": "Rule", "relativeTransform": [[0, 1, 50], [1, 0, 0]], "size": {"x": 80, "y": 0},
         "strokes": [solid(0, 0, 0)], "strokeWeight": 1},
    ]}]}}
    n = by_name(FC.Converter(doc, id_maker(3)).run().finish({}, {}))
    assert n["Hex"]["p"]["type"] == "POLYGON" and n["Hex"]["p"]["sides"] == 6
    assert n["Star"]["p"]["type"] == "STAR" and n["Star"]["p"]["sides"] == 5 and n["Star"]["p"]["ratio"] == pytest.approx(0.38, abs=0.005)
    assert n["Odd"]["p"]["type"] == "VECTOR"
    arc = n["Arc"]["p"]
    assert arc["type"] == "VECTOR" and arc["w"] == 40 and arc["h"] == 20 and arc["y"] == 20
    pen = n["Pen"]["p"]
    assert pen["type"] == "VECTOR" and pen["fills"][0]["color"] == "#FF0000" and "strokes" not in pen and "strokeWeight" not in pen
    line = n["Rule"]["p"]
    assert line["type"] == "LINE" and line["h"] == 0 and line["w"] == 80
    check_matrix(line, FC.from_figma([[0, 1, 50], [1, 0, 0]]), w=80, h=0)


def test_the_layer_cap_is_kept_and_said():
    conv = convert(cap=6)
    ops = conv.finish({}, {})
    made = [o for o in ops if "type" in o["p"]]
    assert len(made) + 2 <= 6
    first = conv.warnings()[0]
    assert "limit" in first["text"] and first["count"] > 10


def test_every_converted_op_passes_the_document_rules():
    ops = convert().finish({"img1": "a" * 64}, {"5:1": "b" * 64})
    doc = Doc(new_document(""))
    assert all(doc.apply(op) == APPLIED for op in ops)
    assert all(len(json.dumps(op)) < 256 * 1024 for op in ops)


# ==================================================================================== the job, through the routes
class FakeFigma:
    """api.figma.com + its image storage. Records every request (headers too)."""

    def __init__(self, doc=None):
        self.doc = doc or figma_file()
        self.calls: list[httpx.Request] = []
        self.status = 200
        self.limit_first = 0
        self.picture = png()

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls.append(req)
        host, path = req.url.host, req.url.path
        if host.endswith("amazonaws.com"):
            assert "x-figma-token" not in req.headers               # the token never leaves for the picture storage
            return httpx.Response(200, content=self.picture, headers={"content-type": "image/png"})
        assert host == "api.figma.com"
        if req.headers.get("x-figma-token") != TOKEN:
            return httpx.Response(403, json={"status": 403, "err": "Invalid token"})
        if self.limit_first > 0:
            self.limit_first -= 1
            return httpx.Response(429, headers={"Retry-After": "7"}, json={"status": 429, "err": "Rate limit exceeded"})
        if self.status != 200:
            return httpx.Response(self.status, json={"status": self.status, "err": "Not found"})
        if path == f"/v1/files/{KEY}":
            assert req.url.params.get("geometry") == "paths"
            return httpx.Response(200, json=self.doc)
        if path == f"/v1/files/{KEY}/images":
            return httpx.Response(200, json={"error": False, "status": 200,
                                             "meta": {"images": {"img1": "https://s3-alpha-sig.figma.amazonaws.com/img/1"}}})
        if path == f"/v1/images/{KEY}":
            ids = req.url.params.get("ids", "").split(",")
            return httpx.Response(200, json={"err": None, "images": {i: f"https://figma-alpha-api.s3.us-west-2.amazonaws.com/r/{i}"
                                                                     for i in ids}})
        return httpx.Response(404, json={"status": 404, "err": "Not found"})


@pytest.fixture()
def fig_env(env, tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "kd")
    monkeypatch.setenv("SECRET_KEY", "test-secret-for-sealing")
    monkeypatch.setenv("DESIGN_DIR", str(tmp_path / "design"))
    from app.config import get_settings
    get_settings.cache_clear()
    fake = FakeFigma()
    figma.set_transport(httpx.MockTransport(fake))
    waits: list[float] = []
    monkeypatch.setattr(figma, "_SLEEP", waits.append)
    figma._JOBS.clear()
    fake.waits = waits
    yield fake
    figma.set_transport(None)
    figma._JOBS.clear()
    get_settings.cache_clear()


def app_client():
    """Only the design router, so the test runs without the whole server's start-up (the job runs on its loop)."""
    from app.design.api import make_router
    from app.main import current_tenant, require_key
    app = FastAPI()
    app.include_router(make_router(require_key, current_tenant))
    return TestClient(app)


def wait_job(c, jid, headers=H, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        r = c.get(f"/api/design/import/{jid}", headers=headers)
        assert r.status_code == 200, r.text
        j = r.json()
        if j["state"] in ("done", "failed"):
            return j
        time.sleep(0.03)
    raise AssertionError("the import did not finish")


def test_token_routes_save_status_forget_and_never_return_the_token(fig_env):
    with app_client() as c:
        assert c.get("/api/design/figma", headers=H).json() == {"linked": False, "hint": ""}
        bad = c.put("/api/design/figma", headers=H, json={"token": "nope"})
        assert bad.status_code == 400 and "personal access token" in bad.json()["detail"]
        r = c.put("/api/design/figma", headers=H, json={"token": TOKEN})
        assert r.status_code == 200 and r.json() == {"ok": True, "linked": True, "hint": "...zz9w"}
        assert TOKEN not in r.text
        from app.config import get_settings
        from app.site import inspire
        me = get_settings().tenant_id
        assert inspire.figma_status(me)["linked"] is True                # the website builder sees the same token
        assert c.get("/api/design/figma", headers=H).json()["linked"] is True
        assert c.delete("/api/design/figma", headers=H).json() == {"ok": True, "linked": False, "hint": ""}
        assert inspire.figma_status(me)["linked"] is False
        assert c.get("/api/design/figma").status_code == 401                 # a key is needed


def test_import_end_to_end_makes_a_normal_file(fig_env, caplog):
    caplog.set_level(logging.DEBUG)
    with app_client() as c:
        none = c.post("/api/design/import/figma", headers=H, json={"url": LINK})
        assert none.status_code == 409 and "Import from Figma" in none.json()["detail"]
        assert c.post("/api/design/import/figma", headers=H, json={"url": "https://example.com/x"}).status_code == 400
        c.put("/api/design/figma", headers=H, json={"token": TOKEN})
        r = c.post("/api/design/import/figma", headers=H, json={"url": LINK})
        assert r.status_code == 200, r.text
        jid = r.json()["job"]["id"]
        assert r.json()["job"]["watch"] == "/console/design#/import/" + jid
        j = wait_job(c, jid)
        assert j["state"] == "done", j
        assert j["name"] == "My App" and j["pages"] == 2 and j["images"] == 1 and j["layers"] > 15
        texts = {w["text"] for w in j["warnings"]}
        assert "Instances of a component that is not in this file (kept as frames, detached)" in texts
        files = c.get("/api/design/files", headers=H).json()["files"]
        assert [f["name"] for f in files] == ["My App"] and files[0]["id"] == j["file"]
        doc = c.get(f"/api/design/files/{j['file']}/doc", headers=H).json()["doc"]
        nodes = doc["nodes"]
        # the stored document obeys the document rules (replayed op by op into a fresh one)
        fresh = Doc(new_document(""))
        order = sorted((nid for nid in nodes if nid not in (ROOT, "0:1")), key=lambda i: int(i.split(":")[1]))
        for nid in order:
            assert fresh.apply({"id": nid, "p": nodes[nid]}) == APPLIED, nid
        photo = next(n for n in nodes.values() if n.get("name") == "Photo")
        sha = photo["fills"][0]["hash"]
        got = c.get(f"/api/design/assets/{sha}", headers=H)
        assert got.status_code == 200 and got.content == fig_env.picture
        note = next(n for n in nodes.values() if n.get("name") == "Note")
        assert note["fills"][0]["hash"] == sha                     # same bytes = one asset
        # every picture address was downloaded once, the file read with geometry=paths
        s3 = [q for q in fig_env.calls if q.url.host.endswith("amazonaws.com")]
        assert len(s3) == len({str(q.url) for q in s3}) == 2
        # the token is in no answer, no job record and no log line
        for text in (r.text, json.dumps(j), json.dumps(figma._JOBS, default=str), caplog.text):
            assert TOKEN not in text


def test_403_404_and_429_are_said_plainly(fig_env):
    with app_client() as c:
        c.put("/api/design/figma", headers=H, json={"token": "figd_" + "B" * 30})          # a token Figma refuses
        j = wait_job(c, c.post("/api/design/import/figma", headers=H, json={"url": LINK}).json()["job"]["id"])
        assert j["state"] == "failed" and "403" in j["error"] and "expired" in j["error"] and 'Figma said: "Invalid token"' in j["error"]
        assert j["file"] is None and c.get("/api/design/files", headers=H).json()["files"] == []
        c.put("/api/design/figma", headers=H, json={"token": TOKEN})
        fig_env.status = 404
        j = wait_job(c, c.post("/api/design/import/figma", headers=H, json={"url": LINK}).json()["job"]["id"])
        assert j["state"] == "failed" and "404" in j["error"] and "no file at this link" in j["error"]
        fig_env.status = 200
        fig_env.limit_first = 2
        j = wait_job(c, c.post("/api/design/import/figma", headers=H, json={"url": LINK}).json()["job"]["id"])
        assert j["state"] == "done" and fig_env.waits == [7.0, 7.0]
        fig_env.limit_first = 9
        j = wait_job(c, c.post("/api/design/import/figma", headers=H, json={"url": LINK}).json()["job"]["id"])
        assert j["state"] == "failed" and "limiting requests" in j["error"]


def test_a_failure_after_the_file_was_made_trashes_it(fig_env, monkeypatch):
    def boom(*a):
        raise RuntimeError("converter exploded")
    monkeypatch.setattr(figma, "_convert", boom)
    with app_client() as c:
        c.put("/api/design/figma", headers=H, json={"token": TOKEN})
        j = wait_job(c, c.post("/api/design/import/figma", headers=H, json={"url": LINK}).json()["job"]["id"])
        assert j["state"] == "failed" and "Hoola's side" in j["error"] and "trash" in j["error"]
        assert "exploded" not in j["error"]
        assert c.get("/api/design/files", headers=H).json()["files"] == []
        assert len(c.get("/api/design/files?trash=1", headers=H).json()["files"]) == 1


def test_jobs_and_files_are_per_tenant(fig_env):
    from app import accounts
    from app.db import User, session
    with session() as s:
        u = User(email="other@example.com", name="Other")
        s.add(u)
        s.flush()
        uid = u.id
    other = {"Authorization": f"Bearer {accounts.issue_session(uid)}"}
    with app_client() as c:
        c.put("/api/design/figma", headers=H, json={"token": TOKEN})
        jid = c.post("/api/design/import/figma", headers=H, json={"url": LINK}).json()["job"]["id"]
        j = wait_job(c, jid)
        assert c.get(f"/api/design/import/{jid}", headers=other).status_code == 404
        assert c.get(f"/api/design/files/{j['file']}/doc", headers=other).status_code == 404
        assert c.get("/api/design/figma", headers=other).json()["linked"] is False     # her token is hers alone
        assert c.post("/api/design/import/figma", headers=other, json={"url": LINK}).status_code == 409


def test_layer_cap_of_the_document_applies_to_an_import(fig_env, monkeypatch):
    monkeypatch.setenv("DESIGN_MAX_NODES", "8")
    from app.config import get_settings
    get_settings.cache_clear()
    with app_client() as c:
        c.put("/api/design/figma", headers=H, json={"token": TOKEN})
        j = wait_job(c, c.post("/api/design/import/figma", headers=H, json={"url": LINK}).json()["job"]["id"])
        assert j["state"] == "done"
        assert "limit" in j["warnings"][0]["text"]
        nodes = c.get(f"/api/design/files/{j['file']}/doc", headers=H).json()["doc"]["nodes"]
        assert len(nodes) <= 8


def test_link_forms():
    assert figma.file_key(f"https://www.figma.com/file/{KEY}/x") == KEY
    assert figma.file_key(f"https://www.figma.com/design/{KEY}/x/branch/ZyXwVuTsRqPoNm/y") == "ZyXwVuTsRqPoNm"
    with pytest.raises(figma.FigmaError):
        figma.file_key(f"https://www.figma.com/board/{KEY}/jam")
    assert figma._image_url_ok("https://s3-alpha-sig.figma.amazonaws.com/a")
    assert not figma._image_url_ok("http://s3-alpha-sig.figma.amazonaws.com/a")
    assert not figma._image_url_ok("https://evil.example.com/a")
    assert not figma._image_url_ok("https://amazonaws.com.evil.example/a")


def test_agent_tool_starts_an_import_and_never_takes_a_token(fig_env):
    import asyncio

    from app.agent import design_tools
    from app.agent.tools import ToolError

    class Ctx:
        tenant_id = "main"
        actor = "owner"

    async def go(**a):
        return await design_tools.hoola_design(Ctx(), action="import_figma", **a)
    with pytest.raises(ToolError) as e:
        asyncio.run(go(url=LINK))
    assert "Import from Figma" in str(e.value)
    with pytest.raises(ToolError) as e:
        asyncio.run(go(url=LINK, token=TOKEN))
    assert "never" in str(e.value).lower() and TOKEN not in str(e.value)
    from app.site import inspire
    inspire.set_figma_token("main", TOKEN)

    async def run_and_wait():
        out = await go(url=LINK)
        for _ in range(400):
            j = figma.job("main", out["job"])
            if j["state"] in ("done", "failed"):
                return out, j
            await asyncio.sleep(0.02)
        raise AssertionError("no finish")
    out, j = asyncio.run(run_and_wait())
    assert out["status"] == "started" and out["watch"].endswith("/console/design#/import/" + out["job"])
    assert j["state"] == "done" and TOKEN not in json.dumps(out)
