"""Google Slides: connecting, building a deck from an outline (layouts, notes, tables), reading, adding / editing /
moving slides, find + replace, export to the phone, delete and share behind confirm cards."""
import asyncio
import copy
import json
import re

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_bazar import _events, bz  # noqa: F401
from tests.test_life import conv_ctx

ME = "meghana@fnw.in"

LAYOUT_PH = {"TITLE": ["CENTERED_TITLE", "SUBTITLE"], "SECTION_HEADER": ["TITLE"], "TITLE_AND_BODY": ["TITLE", "BODY"],
             "TITLE_AND_TWO_COLUMNS": ["TITLE", "BODY", "BODY"], "BIG_NUMBER": ["TITLE", "BODY"], "MAIN_POINT": ["TITLE"],
             "TITLE_ONLY": ["TITLE"], "BLANK": []}


def _shape(oid, ph=None, text=""):
    sh = {"objectId": oid, "shape": {"text": {"textElements": [{"textRun": {"content": text}}] if text else []}}}
    if ph:
        sh["shape"]["placeholder"] = {"type": ph}
    return sh


class FakeSlides:
    def __init__(self):
        self.decks = {}
        self.n = 0
        self.perms = []
        self.calls = []

    def _slide(self, oid, layout="TITLE", ids=None):
        ids = ids or {}
        els = []
        counts = {}
        for ph in LAYOUT_PH[layout]:
            i = counts.get(ph, 0)
            counts[ph] = i + 1
            els.append(_shape(ids.get((ph, i), f"{oid}_{ph}_{i}"), ph))
        return {"objectId": oid, "pageElements": els,
                "slideProperties": {"notesPage": {"notesProperties": {"speakerNotesObjectId": f"{oid}_notes"},
                                                  "pageElements": [_shape(f"{oid}_notes", "BODY")]}}}

    def deck(self, pid, title, slides):
        d = {"presentationId": pid, "title": title, "slides": []}
        for i, (t, body, notes) in enumerate(slides):
            s = self._slide(f"{pid}_s{i}", "TITLE_AND_BODY")
            s["pageElements"][0] = _shape(s["pageElements"][0]["objectId"], "TITLE", t)
            s["pageElements"][1] = _shape(s["pageElements"][1]["objectId"], "BODY", body)
            s["slideProperties"]["notesPage"]["pageElements"][0] = _shape(f"{pid}_s{i}_notes", "BODY", notes)
            d["slides"].append(s)
        self.decks[pid] = d
        return d

    def _find(self, d, oid):
        for s in d["slides"]:
            if s["objectId"] == oid:
                return s
            for el in s["pageElements"] + s["slideProperties"]["notesPage"]["pageElements"]:
                if el["objectId"] == oid:
                    return el
        raise KeyError(oid)

    def _apply(self, d, r):
        (op, a), = r.items()
        if op == "createSlide":
            ids = {(m["layoutPlaceholder"]["type"], m["layoutPlaceholder"].get("index", 0)): m["objectId"]
                   for m in a.get("placeholderIdMappings", [])}
            layout = a["slideLayoutReference"]["predefinedLayout"]
            have = {}
            for ph in LAYOUT_PH[layout]:
                have[ph] = have.get(ph, 0) + 1
            for (ph, i) in ids:
                assert i < have.get(ph, 0), f"layout {layout} has no placeholder {ph}#{i}"
            s = self._slide(a["objectId"], layout, ids)
            d["slides"].insert(a.get("insertionIndex", len(d["slides"])), s)
        elif op == "insertText":
            el = self._find(d, a["objectId"])
            if "cellLocation" in a:
                rows = el["table"]["tableRows"]
                rows[a["cellLocation"]["rowIndex"]]["tableCells"][a["cellLocation"]["columnIndex"]] = \
                    {"text": {"textElements": [{"textRun": {"content": a["text"]}}]}}
            else:
                el["shape"]["text"]["textElements"] = [{"textRun": {"content": a["text"]}}]
        elif op == "deleteText":
            self._find(d, a["objectId"])["shape"]["text"]["textElements"] = []
        elif op == "deleteObject":
            d["slides"] = [s for s in d["slides"] if s["objectId"] != a["objectId"]]
        elif op == "createTable":
            s = self._find(d, a["elementProperties"]["pageObjectId"])
            s["pageElements"].append({"objectId": a["objectId"], "table": {"tableRows": [
                {"tableCells": [{} for _ in range(a["columns"])]} for _ in range(a["rows"])]}})
        elif op == "updateSlidesPosition":
            s = self._find(d, a["slideObjectIds"][0])
            i = d["slides"].index(s)
            d["slides"].insert(a["insertionIndex"], s)
            del d["slides"][i if a["insertionIndex"] > i else i + 1]
        elif op == "duplicateObject":
            s = self._find(d, a["objectId"])
            dup = copy.deepcopy(s)
            self.n += 1
            dup["objectId"] = f"dup{self.n}"
            d["slides"].insert(d["slides"].index(s) + 1, dup)
        elif op == "replaceAllText":
            n = 0
            for s in d["slides"]:
                for el in s["pageElements"]:
                    for te in (el.get("shape") or {}).get("text", {}).get("textElements", []):
                        c = te["textRun"]["content"]
                        k = c.count(a["containsText"]["text"])
                        if k:
                            n += k
                            te["textRun"]["content"] = c.replace(a["containsText"]["text"], a["replaceText"])
            return {"replaceAllText": {"occurrencesChanged": n}}
        return {}

    def __call__(self, req: httpx.Request):
        url = req.url
        try:
            body = json.loads(req.content) if req.content else None
        except ValueError:
            body = None
        self.calls.append((req.method, url.path, dict(url.params), body))
        if url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at", "refresh_token": "rt", "expires_in": 3600,
                                             "scope": "openid email https://www.googleapis.com/auth/presentations "
                                                      "https://www.googleapis.com/auth/drive.metadata.readonly"})
        if url.host == "openidconnect.googleapis.com":
            return httpx.Response(200, json={"email": ME, "name": "Meghana"})
        assert req.headers["authorization"] == "Bearer at"
        if url.host == "www.googleapis.com":
            if url.path == "/drive/v3/files":
                m = re.search(r"name contains '([^']*)'", url.params["q"])
                q = (m.group(1) if m else "").lower()
                return httpx.Response(200, json={"files": [{"id": k, "name": v["title"], "modifiedTime": "2026-10-18T09:00:00Z",
                                                            "webViewLink": f"https://docs.google.com/presentation/d/{k}/edit"}
                                                           for k, v in self.decks.items() if q in v["title"].lower()]})
            if url.path.endswith("/export"):
                return httpx.Response(200, content=b"%PDF-1.4 deck" if "pdf" in url.params["mimeType"] else b"PK\x03\x04pptx")
            if url.path.endswith("/permissions"):
                self.perms.append(body)
                return httpx.Response(200, json={"id": "p"})
        path = url.path.removeprefix("/v1/presentations")
        if path == "" and req.method == "POST":
            self.n += 1
            pid = f"DECK{self.n:036d}"
            d = {"presentationId": pid, "title": body["title"], "slides": [self._slide(f"{pid}_default", "TITLE")]}
            self.decks[pid] = d
            return httpx.Response(200, json=copy.deepcopy(d))
        pid, _, action = path.lstrip("/").partition(":")
        if pid not in self.decks:
            return httpx.Response(404, json={"error": {"message": "not found"}})
        d = self.decks[pid]
        if action == "batchUpdate":
            try:
                replies = [self._apply(d, r) for r in body["requests"]]
            except (AssertionError, KeyError) as e:
                return httpx.Response(400, json={"error": {"message": str(e)}})
            return httpx.Response(200, json={"replies": replies})
        return httpx.Response(200, json=copy.deepcopy(d))


@pytest.fixture
def gsl(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.mailbox import accounts as ma
    fake = FakeSlides()
    fake.deck("OLDDECK00000000000000000000000000000", "FNW Q3 review", [
        ("Q3 review", "Akola, Pune, Nashik", "Welcome everyone"),
        ("Revenue", "Rs 42 lakh, up 18%", "Mention Goa launch"),
        ("Next steps", "Hire 5 field engineers", "")])
    ma.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    from app import main
    with TestClient(main.app) as c:
        url = c.get("/api/slides/link").json()["url"]
        assert "auth%2Fpresentations" in url and "state=gsl_" in url
        page = c.get("/auth/google/callback", params={"code": "c", "state": httpx.URL(url).params["state"]})
        assert page.status_code == 200 and ME in page.text
        assert c.get("/api/slides/accounts").json()["accounts"][0]["address"] == ME
    yield fake
    ma.set_http(None)


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


def _texts(d):
    out = []
    for s in d["slides"]:
        t = []
        for el in s["pageElements"]:
            if "shape" in el:
                t.append("".join(x["textRun"]["content"] for x in el["shape"]["text"]["textElements"]))
            if "table" in el:
                t.append(json.dumps([[c.get("text", {}).get("textElements", [{}])[0].get("textRun", {}).get("content", "")
                                      for c in r["tableCells"]] for r in el["table"]["tableRows"]]))
        out.append(t)
    return out


def test_create_deck_from_outline(gsl):
    ctx = conv_ctx()
    out = run("slides_create", {"title": "FNW Flow pitch", "accent": "#6D3FE0", "slides": [
        {"layout": "title", "title": "FNW Flow", "subtitle": "BSNL FTTH franchise software", "notes": "Namaste"},
        {"layout": "bullets", "title": "Problem", "bullets": ["Manual OLT work", "Late billing", "No field tracking"]},
        {"layout": "two_columns", "title": "Before vs after", "left": ["Excel"], "right": ["One app"]},
        {"layout": "big_number", "number": "22", "caption": "OLTs managed today"},
        {"layout": "table", "title": "Pricing", "rows": [["Plan", "Price"], ["Basic", "Rs 999"]]},
        {"layout": "closing", "title": "Thank you"}]}, ctx)
    d = gsl.decks[out["id"]]
    assert out["slide_count"] == 6 and len(d["slides"]) == 6                    # the blank starter slide is gone
    t = _texts(d)
    assert t[0] == ["FNW Flow", "BSNL FTTH franchise software"]
    assert t[1] == ["Problem", "Manual OLT work\nLate billing\nNo field tracking"]
    assert t[2] == ["Before vs after", "Excel", "One app"] and t[3] == ["22", "OLTs managed today"]
    assert '["Plan", "Price"]' in t[4][1]
    notes = d["slides"][0]["slideProperties"]["notesPage"]["pageElements"][0]["shape"]["text"]["textElements"]
    assert notes[0]["textRun"]["content"] == "Namaste"
    card = _events(ctx.conversation_id, "slides")[-1]
    assert card["title"] == "FNW Flow pitch" and card["link"].endswith("/edit") and card["status"] == "created"


def test_read_find_edit_and_arrange(gsl):
    ctx = conv_ctx()
    found = run("slides_find", {"query": "q3"}, ctx)
    assert found["presentations"][0]["title"] == "FNW Q3 review"
    r = run("slides_read", {"presentation": "FNW Q3 review"}, ctx)
    assert r["slide_count"] == 3 and r["slides"][1] == {"n": 2, "title": "Revenue", "text": "Rs 42 lakh, up 18%",
                                                         "notes": "Mention Goa launch"}
    run("slides_edit", {"presentation": "FNW Q3 review", "slide": 2, "title": "Revenue Q3",
                        "body": ["Rs 42 lakh", "Up 18%"], "notes": "Say thanks to Swati"}, ctx)
    r = run("slides_read", {"presentation": "FNW Q3 review"}, ctx)
    assert r["slides"][1] == {"n": 2, "title": "Revenue Q3", "text": "Rs 42 lakh\nUp 18%", "notes": "Say thanks to Swati"}
    rep = run("slides_edit", {"presentation": "FNW Q3 review", "find": "Akola", "replace": "Akola SSA"}, ctx)
    assert rep["replaced"] == 1
    run("slides_arrange", {"presentation": "FNW Q3 review", "slide": 3, "to": 1}, ctx)
    assert [s["title"] for s in run("slides_read", {"presentation": "FNW Q3 review"}, ctx)["slides"]] == \
        ["Next steps", "Q3 review", "Revenue Q3"]
    run("slides_add", {"presentation": "FNW Q3 review", "position": 2,
                       "slides": [{"layout": "section", "title": "Part 2"}]}, ctx)
    assert [s["title"] for s in run("slides_read", {"presentation": "FNW Q3 review"}, ctx)["slides"]][1] == "Part 2"
    with pytest.raises(ToolError, match="Slide 9 nahi hai"):
        run("slides_edit", {"presentation": "FNW Q3 review", "slide": 9, "title": "x"}, ctx)


def test_export_to_phone(gsl):
    ctx = conv_ctx()
    out = run("slides_export", {"presentation": "FNW Q3 review", "format": "pptx"}, ctx)
    assert out["file"] == "FNW Q3 review.pptx" and out["file_id"]
    assert _events(ctx.conversation_id, "pc_file")[-1]["name"] == "FNW Q3 review.pptx"


def test_delete_and_share_need_the_tap(bz, gsl):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    run("slides_delete", {"presentation": "FNW Q3 review", "slides": [3]}, ctx)
    d = gsl.decks["OLDDECK00000000000000000000000000000"]
    assert len(d["slides"]) == 3
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Slides hatayein?" and "Next steps" in json.dumps(card)
    bz["svc"].decide("default", card["id"], "approve")
    assert len(d["slides"]) == 2
    from app.mailbox import contacts
    contacts.learn("default", [("Swati Sirsath", "swati@fnw.in")], 1.0, sent=True)
    run("slides_share", {"presentation": "FNW Q3 review", "people": ["Swati"], "role": "commenter"}, ctx)
    assert gsl.perms == []
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert gsl.perms == [{"type": "user", "role": "commenter", "emailAddress": "swati@fnw.in"}]
    with pytest.raises(ToolError, match="Saari slides"):
        run("slides_delete", {"presentation": "FNW Q3 review", "slides": [1, 2]}, ctx)


def test_not_connected(env):
    with pytest.raises(ToolError, match="Profile > Google Slides"):
        run("slides_read", {"presentation": "x"}, Ctx("someone", "c"))
