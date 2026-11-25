"""v0.999.188 SLIDES COMPLETE: things on slides, tables, templates with {{blanks}}, pictures of slides, PowerPoint into
Google Slides, rename / copy / bin, comments, who can open a deck, a deck's own layouts, Google's speed limit. The
stand-in for Google checks every request against Google's own Slides API shapes (its discovery document, revision
20261118)."""
import copy
import json
import re

import httpx
import pytest

from app.agent.tools import Ctx, ToolError
from tests.test_bazar import _events, bz  # noqa: F401
from tests.test_life import conv_ctx
from tests.test_slides import FakeSlides, gsl as _gsl, run  # noqa: F401
from tests import test_slides as TS

OLD = "OLDDECK00000000000000000000000000000"
SHEET = "SHEET0000000000000000000000000000000"
SHAPES = {"TEXT_BOX", "RECTANGLE", "ROUND_RECTANGLE", "ELLIPSE", "RIGHT_ARROW", "STAR_5", "TRIANGLE", "HOME_PLATE",
          "WEDGE_ROUND_RECTANGLE_CALLOUT", "CHEVRON"}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 40


class Full(FakeSlides):
    def __init__(self):
        super().__init__()
        self.busy = 0
        self.uploads = []
        self.deleted_perms = []
        self.trashed = []
        self.renamed = {}
        self.batches = []
        self.perm_list = [{"id": "own", "type": "user", "role": "owner", "emailAddress": "meghana@fnw.in"},
                          {"id": "p9", "type": "user", "role": "writer", "emailAddress": "ravi@fnw.in",
                           "displayName": "Ravi"}]

    # ---- Google's shapes, checked ----
    def _apply(self, d, r):
        (op, a), = r.items()
        if op == "createSlide":
            ref = a["slideLayoutReference"]
            assert ("layoutId" in ref) != ("predefinedLayout" in ref), "one of layoutId / predefinedLayout"
            if "layoutId" in ref:
                lay = next(x for x in d.get("layouts", []) if x["objectId"] == ref["layoutId"])
                phs = {e["objectId"]: e["shape"]["placeholder"]["type"] for e in lay["pageElements"]}
                els = []
                for m in a.get("placeholderIdMappings", []):
                    assert m["layoutPlaceholderObjectId"] in phs, "the layout has no such placeholder"
                    els.append(TS._shape(m["objectId"], phs[m["layoutPlaceholderObjectId"]]))
                s = {"objectId": a["objectId"], "pageElements": els, "slideProperties": {
                    "layoutObjectId": lay["objectId"],
                    "notesPage": {"notesProperties": {"speakerNotesObjectId": a["objectId"] + "_notes"},
                                  "pageElements": [TS._shape(a["objectId"] + "_notes", "BODY")]}}}
                d["slides"].insert(a.get("insertionIndex", len(d["slides"])), s)
                return {}
            return super()._apply(d, r)
        if op == "createShape":
            assert a["shapeType"] in SHAPES, a["shapeType"]
            self._page(d, a)["pageElements"].append({"objectId": a["objectId"], **self._geo(a),
                                                     "shape": {"shapeType": a["shapeType"], "text": {"textElements": []}}})
        elif op == "createImage":
            assert a["url"].startswith("https://")
            self._page(d, a)["pageElements"].append({"objectId": a["objectId"], **self._geo(a), "image": {"sourceUrl": a["url"]}})
        elif op == "createVideo":
            assert a["source"] in ("YOUTUBE", "DRIVE") and a["id"]
            self._page(d, a)["pageElements"].append({"objectId": a["objectId"], **self._geo(a),
                                                     "video": {"source": a["source"], "id": a["id"]}})
        elif op == "createLine":
            assert a["category"] in ("STRAIGHT", "BENT", "CURVED") and "lineCategory" not in a
            self._page(d, a)["pageElements"].append({"objectId": a["objectId"], **self._geo(a), "line": {}})
        elif op == "createSheetsChart":
            assert a["spreadsheetId"] == SHEET and isinstance(a["chartId"], int) and a["linkingMode"] in ("LINKED",
                                                                                                         "NOT_LINKED_IMAGE")
            self._page(d, a)["pageElements"].append({"objectId": a["objectId"], **self._geo(a), "sheetsChart": {
                "spreadsheetId": a["spreadsheetId"], "chartId": a["chartId"]}})
        elif op == "createTable":
            out = super()._apply(d, r)
            t = self._find(d, a["objectId"])
            t["table"]["rows"], t["table"]["columns"] = a["rows"], a["columns"]
            return out
        elif op in ("updateTextStyle", "updateParagraphStyle", "updateShapeProperties", "updatePageProperties",
                    "updateSlideProperties", "updateLineProperties", "updateTableCellProperties",
                    "updateTableColumnProperties", "updateImageProperties"):
            assert a.get("fields"), f"{op} needs fields"
            for f in a["fields"].split(","):
                assert f and " " not in f
            if op == "updateSlideProperties":
                self._find(d, a["objectId"])["slideProperties"]["isSkipped"] = a["slideProperties"]["isSkipped"]
            if op == "updatePageProperties":
                assert a["fields"].startswith("pageBackgroundFill.")
                self._find(d, a["objectId"]).setdefault("pageProperties", {}).update(a["pageProperties"])
            if op == "updateTextStyle" and "fontSize" in a["style"]:
                assert a["style"]["fontSize"]["unit"] == "PT"
        elif op == "updatePageElementTransform":
            assert a["applyMode"] == "ABSOLUTE" and a["transform"]["unit"] == "EMU"
            self._find(d, a["objectId"])["transform"] = a["transform"]
        elif op == "updatePageElementsZOrder":
            assert a["operation"] in ("BRING_TO_FRONT", "BRING_FORWARD", "SEND_BACKWARD", "SEND_TO_BACK")
        elif op == "updatePageElementAltText":
            el = self._find(d, a["objectId"])
            el["description"] = a["description"]
        elif op == "deleteObject":
            for s in d["slides"]:
                s["pageElements"] = [e for e in s["pageElements"] if e["objectId"] != a["objectId"]]
            return super()._apply(d, r)
        elif op == "refreshSheetsChart":
            assert "sheetsChart" in self._find(d, a["objectId"])
        elif op in ("insertTableRows", "insertTableColumns"):
            t = self._find(d, a["tableObjectId"])["table"]
            assert a["number"] >= 1 and "cellLocation" in a
            if op == "insertTableRows":
                at = a["cellLocation"]["rowIndex"] + (1 if a["insertBelow"] else 0)
                for _ in range(a["number"]):
                    t["tableRows"].insert(at, {"tableCells": [{} for _ in range(t["columns"])]})
                t["rows"] += a["number"]
            else:
                at = a["cellLocation"]["columnIndex"] + (1 if a["insertRight"] else 0)
                for row in t["tableRows"]:
                    for _ in range(a["number"]):
                        row["tableCells"].insert(at, {})
                t["columns"] += a["number"]
        elif op == "deleteTableRow":
            t = self._find(d, a["tableObjectId"])["table"]
            del t["tableRows"][a["cellLocation"]["rowIndex"]]
            t["rows"] -= 1
        elif op in ("mergeTableCells", "unmergeTableCells"):
            tr = a["tableRange"]
            assert tr["rowSpan"] >= 1 and tr["columnSpan"] >= 1 and "location" in tr
        elif op == "deleteText" and "cellLocation" in a:
            t = self._find(d, a["objectId"])["table"]
            t["tableRows"][a["cellLocation"]["rowIndex"]]["tableCells"][a["cellLocation"]["columnIndex"]] = {}
        elif op == "replaceAllShapesWithImage":
            assert "imageReplaceMethod" in a and "replaceMethod" not in a and a["containsText"]["matchCase"] is True
            n = 0
            for s in d["slides"]:
                for el in list(s["pageElements"]):
                    if "shape" in el and a["containsText"]["text"] in TS._texts({"slides": [{"pageElements": [el]}]})[0][0]:
                        el.pop("shape")
                        el["image"] = {"sourceUrl": a["imageUrl"]}
                        n += 1
            return {"replaceAllShapesWithImage": {"occurrencesChanged": n}}
        elif op == "replaceAllText":
            if "pageObjectIds" in a:
                keep = d["slides"]
                d["slides"] = [s for s in keep if s["objectId"] in a["pageObjectIds"]]
                try:
                    return super()._apply(d, r)
                finally:
                    d["slides"] = keep
            return super()._apply(d, r)
        elif op == "insertComment":
            assert a["objectId"] and 0 < len(a["content"]) <= 2048
            self.n += 1
            th = {"commentId": f"c{self.n}", "status": "OPEN", "headPost": {"content": a["content"],
                                                                          "author": {"displayName": "Meghana"}},
                  "replies": []}
            d.setdefault("comments", []).append(th)
            return {"insertComment": {"commentThread": th}}
        elif op == "addCommentReply":
            th = next(t for t in d.get("comments", []) if t["commentId"] == a["commentId"])
            th["replies"].append({"content": a["post"]["content"]})
            act = a["post"].get("commentAction")
            assert act in (None, "RESOLVE", "REOPEN")
            if act:
                th["status"] = "RESOLVED" if act == "RESOLVE" else "OPEN"
        elif op == "deleteComment":
            d["comments"] = [t for t in d.get("comments", []) if t["commentId"] != a["commentId"]]
        else:
            return super()._apply(d, r)
        return {}

    def _page(self, d, a):
        return self._find(d, a["elementProperties"]["pageObjectId"])

    @staticmethod
    def _geo(a):
        ep = a["elementProperties"]
        assert ep["size"]["width"]["unit"] == "EMU" and ep["transform"]["unit"] == "EMU"
        return {"size": ep["size"], "transform": ep["transform"]}

    def __call__(self, req: httpx.Request):
        url = req.url
        if url.host == "lh3.googleusercontent.com":
            assert "authorization" not in req.headers
            return httpx.Response(200, content=PNG)
        if url.host in ("oauth2.googleapis.com", "openidconnect.googleapis.com"):
            return super().__call__(req)
        assert req.headers["authorization"] == "Bearer at"
        if self.busy:
            self.busy -= 1
            return httpx.Response(429, json={"error": {"message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}})
        body = None
        if req.content and req.headers.get("content-type", "").startswith("application/json"):
            body = json.loads(req.content)
        if url.host == "sheets.googleapis.com":
            return httpx.Response(200, json={"properties": {"title": "Sales 2026"}, "sheets": [
                {"properties": {"title": "Q3"}, "charts": [{"chartId": 777, "spec": {"title": "Revenue by month"}}]}]})
        if url.host == "www.googleapis.com" and url.path.startswith("/upload/drive/v3/files"):
            raw = req.content
            meta = json.loads(re.search(rb"\r\n\r\n(\{.*?\})\r\n", raw).group(1))
            self.uploads.append((meta, req.headers["content-type"], raw))
            self.n += 1
            pid = f"IMPORTED{self.n:030d}"
            self.decks[pid] = {"presentationId": pid, "title": meta["name"], "slides": [self._slide(pid + "_s0", "TITLE")]}
            return httpx.Response(200, json={"id": pid, "name": meta["name"]})
        if url.host == "www.googleapis.com":
            m = re.fullmatch(r"/drive/v3/files/([^/]+)(/.*)?", url.path)
            if m and m.group(2) == "/copy":
                src = self.decks[m.group(1)]
                self.n += 1
                pid = f"COPY{self.n:034d}"
                d = copy.deepcopy(src)
                d["presentationId"], d["title"] = pid, body["name"]
                self.decks[pid] = d
                return httpx.Response(200, json={"id": pid, "name": body["name"]})
            if m and m.group(2) is None and req.method == "PATCH":
                if body.get("trashed"):
                    self.trashed.append(m.group(1))
                if body.get("name"):
                    self.renamed[m.group(1)] = body["name"]
                    self.decks[m.group(1)]["title"] = body["name"]
                return httpx.Response(200, json={"id": m.group(1)})
            if m and m.group(2) == "/permissions" and req.method == "GET":
                return httpx.Response(200, json={"permissions": self.perm_list})
            if m and m.group(2) and m.group(2).startswith("/permissions/") and req.method == "DELETE":
                self.deleted_perms.append(m.group(2).rsplit("/", 1)[1])
                return httpx.Response(204)
        if url.host == "slides.googleapis.com" and "/pages/" in url.path:
            assert url.params["thumbnailProperties.thumbnailSize"] in ("SMALL", "MEDIUM", "LARGE", "WIDTH2000_PX")
            return httpx.Response(200, json={"contentUrl": "https://lh3.googleusercontent.com/thumb/" + url.path[-6:]})
        if url.host == "slides.googleapis.com" and url.path.endswith(":batchUpdate"):
            self.batches.append(body)
            assert set(body) <= {"requests", "writeControl"}
            for r in body["requests"]:
                assert len(r) == 1 and next(iter(r)) in REQUEST_KINDS, r
        if url.host == "slides.googleapis.com" and req.method == "GET" and "commentsViewMode" in url.params:
            assert url.params["commentsViewMode"] == "COMMENTS_VIEW_MODE_INCLUDED"
        return super().__call__(req)


REQUEST_KINDS = set("""addCommentReply createImage createLine createParagraphBullets createShape createSheetsChart
createSlide createTable createVideo deleteComment deleteCommentReply deleteObject deleteParagraphBullets
deleteTableColumn deleteTableRow deleteText duplicateObject groupObjects insertComment insertTableColumns insertTableRows
insertText mergeTableCells refreshSheetsChart replaceAllShapesWithImage replaceAllShapesWithSheetsChart replaceAllText
replaceImage rerouteLine ungroupObjects unmergeTableCells updateCommentPost updateImageProperties updateLineCategory
updateLineProperties updatePageElementAltText updatePageElementTransform updatePageElementsZOrder updatePageProperties
updateParagraphStyle updateShapeProperties updateSlideProperties updateSlidesPosition updateTableBorderProperties
updateTableCellProperties updateTableColumnProperties updateTableRowProperties updateTextStyle updateVideoProperties""".split())


@pytest.fixture
def gs(env, monkeypatch):
    """The test_slides fixture, on the stand-in that checks Google's shapes."""
    monkeypatch.setattr(TS, "FakeSlides", Full)
    from app.slides.client import SlidesClient
    monkeypatch.setattr(SlidesClient, "RETRY_WAIT", 0.0)
    gen = TS.gsl.__wrapped__(env, monkeypatch)
    fake = next(gen)
    yield fake
    try:
        next(gen)
    except StopIteration:
        pass


def _deck(fake):
    return fake.decks[OLD]


def _store(name, data, tenant="default"):
    from app.mailbox import service as ms
    return ms.store_bytes(tenant, name, data, "to_phone").id


def test_design_adds_things_in_googles_shapes(gs):
    ctx = conv_ctx()
    P = "FNW Q3 review"
    out = run("slides_design", {"presentation": P, "slide": 2, "action": "add", "kind": "text", "text": "Rs 42 lakh",
                                "place": "bottom_right", "style": {"bold": True, "size": 28, "color": "#6D3FE0",
                                                                   "align": "center", "alt": "Revenue"}}, ctx)
    box = TS.json.dumps(_deck(gs)["slides"][1]["pageElements"][-1])
    assert out["added"] == "text" and "TEXT_BOX" in box
    run("slides_design", {"presentation": P, "slide": 2, "action": "add", "kind": "shape", "shape": "arrow",
                          "text": "Next", "style": {"fill": "#FFB15C", "no_outline": True}}, ctx)
    run("slides_design", {"presentation": P, "slide": 2, "action": "add", "kind": "image",
                          "image_url": "https://example.in/logo.png", "place": "top_right"}, ctx)
    run("slides_design", {"presentation": P, "slide": 2, "action": "add", "kind": "video",
                          "video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}, ctx)
    run("slides_design", {"presentation": P, "slide": 2, "action": "add", "kind": "line", "x": 40, "y": 300,
                          "line_to": {"x": 680, "y": 300}, "style": {"color": "#000000", "width": 2, "arrow": True}}, ctx)
    run("slides_design", {"presentation": P, "slide": 3, "action": "add", "kind": "chart", "sheet":
                          f"https://docs.google.com/spreadsheets/d/{SHEET}/edit", "chart": "revenue"}, ctx)
    run("slides_design", {"presentation": P, "slide": 3, "action": "add", "kind": "table",
                          "rows": [["City", "Sales"], ["Akola", "12"]]}, ctx)
    with pytest.raises(ToolError, match="not a Google Slides shape"):
        run("slides_design", {"presentation": P, "slide": 2, "action": "add", "kind": "shape", "shape": "spaceship"}, ctx)
    r = run("slides_read", {"presentation": P, "slides": [2, 3], "details": True}, ctx)
    kinds = [e["kind"] for e in r["slides"][0]["elements"]]
    assert kinds[-5:] == ["text", "shape", "image", "video", "line"]
    assert {m["kind"] for m in r["slides"][1]["media"]} == {"chart"} and r["slides"][1]["tables"]
    text_el = r["slides"][0]["elements"][2]
    assert text_el["text"] == "Rs 42 lakh" and text_el["alt"] == "Revenue" and text_el["x"] > 300
    # move + resize = one ABSOLUTE transform with the right scale; then style + order + remove
    run("slides_design", {"presentation": P, "slide": 2, "action": "change", "element": "Rs 42 lakh",
                          "x": 100, "y": 100, "w": 216, "text": "Rs 45 lakh"}, ctx)
    el = next(e for e in _deck(gs)["slides"][1]["pageElements"] if e["objectId"] == text_el["id"])
    assert round(el["transform"]["scaleX"], 3) == round(216 / text_el["w"], 3) and el["transform"]["translateX"] == 100 * 12700
    run("slides_design", {"presentation": P, "slide": 2, "action": "order", "element": text_el["id"], "order": "front"}, ctx)
    run("slides_design", {"presentation": P, "slide": 2, "action": "background", "background": "#F4F2FF",
                          "all_slides": True}, ctx)
    assert all(s["pageProperties"]["pageBackgroundFill"]["solidFill"] for s in _deck(gs)["slides"])
    run("slides_design", {"presentation": P, "slide": 3, "action": "refresh_charts"}, ctx)
    run("slides_design", {"presentation": P, "slide": 2, "action": "remove", "element": text_el["id"]}, ctx)
    assert all(e["objectId"] != text_el["id"] for e in _deck(gs)["slides"][1]["pageElements"])


def test_group_text_is_read(gs):
    d = _deck(gs)
    d["slides"][0]["pageElements"].append({"objectId": "g1", "elementGroup": {"children": [
        TS._shape("g1a", None, "Inside a group")]}})
    r = run("slides_read", {"presentation": "FNW Q3 review", "slides": [1]}, conv_ctx())
    assert "Inside a group" in r["slides"][0]["text"]


def test_photo_from_the_chat_signed_link(gs):
    from fastapi.testclient import TestClient
    from app import main
    from app.slides import more
    fid = _store("logo.png", PNG)
    url = more.image_link("default", fid)
    assert url.startswith("https://s.example.in/api/slides/img/")
    path = url.split("s.example.in", 1)[1]
    with TestClient(main.app) as c:
        r = c.get(path)
        assert r.status_code == 200 and r.content == PNG and r.headers["content-type"] == "image/png"
        assert c.get(path.replace("s=", "s=x")).status_code == 404
    with pytest.raises(Exception, match="not a PNG, JPEG or GIF"):
        more.image_link("default", _store("notes.txt", b"hello"))
    run("slides_design", {"presentation": "FNW Q3 review", "slide": 1, "action": "add", "kind": "image", "file_id": fid},
        conv_ctx())
    assert any("image" in e for e in _deck(gs)["slides"][0]["pageElements"])


def test_template_and_its_own_layouts(gs):
    ctx = conv_ctx()
    T = "TEMPLATE00000000000000000000000000000"
    gs.decks[T] = {"presentationId": T, "title": "FNW brand template", "layouts": [
        {"objectId": "L1", "layoutProperties": {"name": "Brand title", "displayName": "Brand title + body"},
         "pageElements": [TS._shape("L1_t", "TITLE"), TS._shape("L1_b", "BODY")]},
        {"objectId": "L2", "layoutProperties": {"name": "Cover", "displayName": "Cover"},
         "pageElements": [TS._shape("L2_t", "CENTERED_TITLE"), TS._shape("L2_s", "SUBTITLE")]}],
        "slides": [gs._slide(T + "_s0", "TITLE")]}
    out = run("slides_create", {"title": "Pitch in our look", "template": "FNW brand template", "slides": [
        {"layout": "title", "title": "FNW Flow", "subtitle": "For franchises"},
        {"layout": "bullets", "title": "Why", "bullets": ["Fast", "Cheap"]},
        {"layout": "two_columns", "title": "Compare", "left": ["Old"], "right": ["New"]}]}, ctx)
    d = gs.decks[out["id"]]
    assert out["template"] == "FNW brand template" and len(d["slides"]) == 3 and out["id"].startswith("COPY")
    assert [s["slideProperties"]["layoutObjectId"] for s in d["slides"]] == ["L2", "L1", "L1"]
    assert TS._texts(d)[1] == ["Why", "Fast\nCheap"]
    assert any("no right box" in n for n in out["notes"])          # her layout has one body box: said, not hidden
    add = run("slides_add", {"presentation": out["id"], "slides": [{"layout": "bullets", "layout_name": "brand title",
                                                                    "title": "More", "bullets": ["x"]}]}, ctx)
    assert add["added"] == 1 and d["slides"][-1]["slideProperties"]["layoutObjectId"] == "L1"
    with pytest.raises(ToolError, match="no layout called 'Fancy'"):
        run("slides_add", {"presentation": out["id"], "slides": [{"layout": "bullets", "layout_name": "Fancy"}]}, ctx)


def test_fill_blanks_copies_and_card(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    d = _deck(gs)
    d["slides"][0]["pageElements"][0] = TS._shape(d["slides"][0]["pageElements"][0]["objectId"], "TITLE",
                                                  "Offer for {{name}}")
    d["slides"][1]["pageElements"].append(TS._shape("logo_box", None, "{{logo}}"))
    two = run("slides_fill", {"presentation": "FNW Q3 review", "copies": [
        {"name": "Offer - Asha", "values": {"name": "Asha"}, "images": {"logo": "https://example.in/a.png"}},
        {"name": "Offer - Ravi", "values": {"name": "Ravi", "city": "Pune"}}]}, ctx)
    assert set(two["blanks"]) == {"name", "logo"} and two["unknown_blanks"] == ["city"]
    asha = gs.decks[two["made"][0]["id"]]
    assert TS._texts(asha)[0][0] == "Offer for Asha" and two["made"][1]["blanks_left"] == ["logo"]
    assert any("image" in e for e in asha["slides"][1]["pageElements"])
    assert TS._texts(d)[0][0] == "Offer for {{name}}"                  # the template itself is untouched
    many = run("slides_fill", {"presentation": "FNW Q3 review", "copies": [
        {"name": f"Offer {i}", "values": {"name": f"P{i}"}} for i in range(5)]}, ctx)
    assert many["status"] == "needs_approval" and len(gs.decks) == 3
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Make the copies?"
    bz["svc"].decide("default", card["id"], "approve")
    assert len(gs.decks) == 8
    inplace = run("slides_fill", {"presentation": "FNW Q3 review", "in_place": True, "values": {"name": "Everyone"}}, ctx)
    assert inplace["changed"] == 1 and inplace["blanks_left"] == ["logo"]
    with pytest.raises(ToolError, match="no \\{\\{blanks\\}\\}"):
        run("slides_fill", {"presentation": two["made"][0]["id"], "in_place": True, "values": {"x": "y"}}, ctx)


def test_tables(gs):
    ctx = conv_ctx()
    P = "FNW Q3 review"
    run("slides_design", {"presentation": P, "slide": 1, "action": "add", "kind": "table",
                          "rows": [["City", "Sales"], ["Akola", "12"]]}, ctx)
    run("slides_table", {"presentation": P, "slide": 1, "action": "add_rows", "row": 2, "values": [["Pune", "30"]]}, ctx)
    t = next(e for e in _deck(gs)["slides"][0]["pageElements"] if "table" in e)["table"]
    assert t["rows"] == 3 and t["tableRows"][2]["tableCells"][0]["text"]["textElements"][0]["textRun"]["content"] == "Pune"
    run("slides_table", {"presentation": P, "slide": 1, "action": "add_columns"}, ctx)
    run("slides_table", {"presentation": P, "slide": 1, "action": "cell", "row": 1, "column": 3, "text": "Target",
                         "style": {"bold": True, "fill": "#FFD9A8"}}, ctx)
    run("slides_table", {"presentation": P, "slide": 1, "action": "merge", "row": 2, "column": 1, "rows": 2}, ctx)
    run("slides_table", {"presentation": P, "slide": 1, "action": "delete_row", "row": 3}, ctx)
    assert t["rows"] == 2
    with pytest.raises(ToolError, match="32 points"):
        run("slides_table", {"presentation": P, "slide": 1, "action": "column_width", "column": 1,
                             "style": {"width": 10}}, ctx)
    with pytest.raises(ToolError, match="2 rows and 3 columns"):
        run("slides_table", {"presentation": P, "slide": 1, "action": "cell", "row": 9, "column": 1, "text": "x"}, ctx)


def test_look_import_and_deck_file(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("slides_look", {"presentation": "FNW Q3 review", "slides": [1, 3], "size": "large"}, ctx)
    assert [p["slide"] for p in out["pictures"]] == [1, 3]
    assert _events(bz["conv"], "pc_file")[-1]["name"] == "FNW Q3 review - slide 3.png"
    fid = _store("Board deck.pptx", b"PK\x03\x04 a real pptx")
    imp = run("slides_import", {"file_id": fid}, ctx)
    meta, ctype, raw = gs.uploads[-1]
    assert meta == {"name": "Board deck", "mimeType": "application/vnd.google-apps.presentation"}
    assert ctype.startswith("multipart/related") and b"presentationml.presentation" in raw
    assert imp["title"] == "Board deck" and imp["slide_count"] == 1
    with pytest.raises(ToolError, match="not one of those"):
        run("slides_import", {"file_id": _store("notes.docx", b"PK..")}, ctx)
    ren = run("slides_deck", {"presentation": "FNW Q3 review", "action": "rename", "name": "FNW Q3 review final"}, ctx)
    assert gs.renamed[OLD] == "FNW Q3 review final" and ren["was"] == "FNW Q3 review"
    cp = run("slides_deck", {"presentation": OLD, "action": "copy"}, ctx)
    assert gs.decks[cp["id"]]["title"] == "Copy of FNW Q3 review final"
    tr = run("slides_deck", {"presentation": OLD, "action": "trash"}, ctx)
    assert tr["status"] == "needs_approval" and gs.trashed == []
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Move the presentation to the bin?"
    bz["svc"].decide("default", card["id"], "approve")
    assert gs.trashed == [OLD]


def test_comments(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    add = run("slides_comments", {"presentation": "FNW Q3 review", "action": "add", "slide": 2,
                                  "text": "Check the 18% figure"}, ctx)
    assert add["comment_id"] == "c1"
    ins = [r for b in gs.batches for r in b["requests"] if "insertComment" in r][-1]["insertComment"]
    assert ins["objectId"] == _deck(gs)["slides"][1]["objectId"]
    run("slides_comments", {"presentation": "FNW Q3 review", "action": "reply", "comment": "c1", "text": "Done"}, ctx)
    run("slides_comments", {"presentation": "FNW Q3 review", "action": "resolve", "comment": "c1"}, ctx)
    lst = run("slides_comments", {"presentation": "FNW Q3 review"}, ctx)
    assert lst["comments"][0]["status"] == "resolved" and lst["comments"][0]["text"] == "Check the 18% figure"
    assert [r["text"] for r in lst["comments"][0]["replies"]] == ["Done", "Resolved."]
    run("slides_comments", {"presentation": "FNW Q3 review", "action": "delete", "comment": "c1"}, ctx)
    assert _deck(gs)["comments"]
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert _deck(gs)["comments"] == []


def test_access_list_remove_link_and_drive_fallback(bz, gs, monkeypatch):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    lst = run("slides_share", {"presentation": "FNW Q3 review", "action": "list"}, ctx)
    assert [p["who"] for p in lst["people"]] == ["meghana@fnw.in", "ravi@fnw.in"]
    rm = run("slides_share", {"presentation": "FNW Q3 review", "action": "remove", "people": ["Ravi"]}, ctx)
    assert rm["status"] == "needs_approval" and gs.deleted_perms == []
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert gs.deleted_perms == ["p9"]
    run("slides_share", {"presentation": "FNW Q3 review", "action": "link"}, ctx)
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Let anyone with the link open it?"
    bz["svc"].decide("default", card["id"], "approve")
    assert gs.perms[-1] == {"type": "anyone", "role": "reader"}
    # a deck Hoola did not make: Drive refuses the Slides connection, her Drive connection does it
    from app.slides import service as sv
    from app.slides.client import SlidesClient, SlidesError

    def refuse(self, pid, name):
        raise SlidesError("You do not have permission for this presentation")
    monkeypatch.setattr(SlidesClient, "copy", refuse)

    class Drive:
        address = "meghana@fnw.in"

        def copy(self, pid, name):
            return {"id": "FROMDRIVE0000000000000000000000000000"}
    monkeypatch.setattr(sv, "drive_for", lambda tenant, address: Drive())
    assert sv.copy_deck("default", sv.get_client("default"), OLD, "x") == "FROMDRIVE0000000000000000000000000000"
    monkeypatch.setattr(sv, "drive_for", lambda tenant, address: None)
    with pytest.raises(SlidesError, match="Connecting Google Drive"):
        sv.copy_deck("default", sv.get_client("default"), OLD, "x")


def test_speed_limit_skip_scoped_replace_and_english(gs):
    ctx = conv_ctx()
    gs.busy = 2
    r = run("slides_read", {"presentation": "FNW Q3 review"}, ctx)
    assert r["slide_count"] == 3 and gs.busy == 0
    gs.busy = 9
    with pytest.raises(ToolError, match="busy"):
        run("slides_read", {"presentation": "FNW Q3 review"}, ctx)
    gs.busy = 0
    run("slides_edit", {"presentation": "FNW Q3 review", "slide": 3, "skip": True}, ctx)
    assert run("slides_read", {"presentation": "FNW Q3 review"}, ctx)["slides"][2]["skipped"] is True
    rep = run("slides_edit", {"presentation": "FNW Q3 review", "find": "e", "replace": "E", "only_slides": [2]}, ctx)
    assert rep["replaced"] >= 1 and TS._texts(_deck(gs))[0][0] == "Q3 review"
    with pytest.raises(ToolError, match="Which slides should go"):
        run("slides_delete", {"presentation": "FNW Q3 review", "slides": []}, ctx)
    out = run("slides_export", {"presentation": "FNW Q3 review", "format": "odp"}, ctx)
    assert out["file"] == "FNW Q3 review.odp"


def test_tool_count_and_family():
    from app.agent.slides_tools import SLIDES_HANDLERS, SLIDES_LABELS, SLIDES_TOOLS
    assert len(SLIDES_TOOLS) == 16 and set(SLIDES_HANDLERS) == set(SLIDES_LABELS) == {t["name"] for t in SLIDES_TOOLS}
    from app.agent.tools import TOOLS
    assert {"slides_design", "slides_table", "slides_fill", "slides_look", "slides_import", "slides_deck",
            "slides_comments"} <= {t["name"] for t in TOOLS}
