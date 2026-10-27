"""Google Sheets: connecting, finding by name, reading, exact queries with totals, adding / editing rows, deleting
and sharing behind confirm cards, creating and importing, exporting to the phone."""
import asyncio
import io
import json
import re
from urllib.parse import unquote

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_bazar import _events, bz  # noqa: F401
from tests.test_life import conv_ctx

ME = "meghana@fnw.in"
SID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd"


def _cell_ref(a1):
    m = re.fullmatch(r"([A-Z]+)(\d+)", a1)
    col = 0
    for ch in m.group(1):
        col = col * 26 + ord(ch) - 64
    return int(m.group(2)) - 1, col - 1


class FakeSheets:
    def __init__(self):
        self.books = {}         # id -> {"title", "tabs": {name: {"id": n, "grid": [[...]]}}}
        self.calls = []
        self.perms = []
        self.n = 0

    def book(self, sid, title, tabs):
        self.books[sid] = {"title": title, "tabs": {name: {"id": i, "grid": [list(r) for r in grid]}
                                                    for i, (name, grid) in enumerate(tabs.items())}}

    def _split(self, rng, sid):
        rng = unquote(rng)
        if "!" in rng:
            tab, cells = rng.split("!", 1)
        else:
            tab, cells = rng, ""
        tab = tab.strip("'").replace("''", "'")
        b = self.books[sid]["tabs"]
        if tab not in b:
            tab, cells = next(iter(b)), rng
        return tab, cells

    def _write(self, sid, rng, values):
        tab, cells = self._split(rng, sid)
        grid = self.books[sid]["tabs"][tab]["grid"]
        r0, c0 = _cell_ref(cells.split(":")[0]) if cells else (0, 0)
        n = 0
        for i, row in enumerate(values):
            while len(grid) <= r0 + i:
                grid.append([])
            g = grid[r0 + i]
            for j, v in enumerate(row):
                while len(g) <= c0 + j:
                    g.append("")
                g[c0 + j] = v
                n += 1
        return n

    def __call__(self, req: httpx.Request):
        url = req.url
        try:
            body = json.loads(req.content) if req.content else None
        except ValueError:
            body = None
        self.calls.append((req.method, url.path, dict(url.params), body))
        if url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at", "refresh_token": "rt", "expires_in": 3600,
                                             "scope": "openid email https://www.googleapis.com/auth/spreadsheets "
                                                      "https://www.googleapis.com/auth/drive.metadata.readonly"})
        if url.host == "openidconnect.googleapis.com":
            return httpx.Response(200, json={"email": ME, "name": "Meghana"})
        assert req.headers["authorization"] == "Bearer at"
        if url.host == "www.googleapis.com" and url.path == "/drive/v3/files":
            m = re.search(r"name contains '([^']*)'", url.params["q"])
            q = (m.group(1) if m else "").lower()
            files = [{"id": k, "name": v["title"], "modifiedTime": "2026-10-18T10:00:00Z",
                      "webViewLink": f"https://docs.google.com/spreadsheets/d/{k}/edit"}
                     for k, v in self.books.items() if q in v["title"].lower()]
            return httpx.Response(200, json={"files": files})
        if url.host == "www.googleapis.com" and url.path.endswith("/permissions"):
            self.perms.append(body)
            return httpx.Response(200, json={"id": "p1"})
        path = url.path.removeprefix("/v4/spreadsheets")
        if path == "" and req.method == "POST":
            self.n += 1
            sid = f"NEW{self.n:040d}"
            self.book(sid, body["properties"]["title"], {s["properties"]["title"]: [] for s in body["sheets"]})
            return httpx.Response(200, json={"spreadsheetId": sid, "properties": {"title": body["properties"]["title"]},
                                             "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{sid}/edit",
                                             "sheets": [{"properties": {"sheetId": t["id"], "title": n}}
                                                        for n, t in self.books[sid]["tabs"].items()]})
        sid, _, rest = path.lstrip("/").partition("/")
        action = ""
        if ":" in sid:
            sid, action = sid.split(":", 1)
        if sid not in self.books:
            return httpx.Response(404, json={"error": {"message": "not found"}})
        bk = self.books[sid]
        if not rest and not action and req.method == "GET":
            return httpx.Response(200, json={"spreadsheetId": sid, "properties": {"title": bk["title"]},
                                             "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{sid}/edit",
                                             "sheets": [{"properties": {"sheetId": t["id"], "title": n, "index": t["id"],
                                                                        "gridProperties": {"rowCount": 1000, "columnCount": 26}}}
                                                        for n, t in bk["tabs"].items()]})
        if action == "batchUpdate":
            for r in body["requests"]:
                if "deleteDimension" in r:
                    rg = r["deleteDimension"]["range"]
                    tab = next(t for t in bk["tabs"].values() if t["id"] == rg["sheetId"])
                    del tab["grid"][rg["startIndex"]:rg["endIndex"]]
                if "addSheet" in r:
                    bk["tabs"][r["addSheet"]["properties"]["title"]] = {"id": len(bk["tabs"]), "grid": []}
            return httpx.Response(200, json={})
        if rest == "values:batchUpdate":
            n = sum(self._write(sid, d["range"], d["values"]) for d in body["data"])
            return httpx.Response(200, json={"totalUpdatedCells": n})
        if rest == "values:batchGet":
            out = []
            for rng in url.params.get_list("ranges"):
                tab, cells = self._split(rng, sid)
                grid = bk["tabs"][tab]["grid"]
                out.append({"values": [[str(c) for c in r] for r in (grid[:1] if cells == "A1:ZZ1" else grid)]})
            return httpx.Response(200, json={"valueRanges": out})
        if rest.startswith("values/") and rest.endswith(":append"):
            tab, _ = self._split(rest[len("values/"):-len(":append")], sid)
            grid = bk["tabs"][tab]["grid"]
            start = len(grid) + 1
            grid.extend([list(r) for r in body["values"]])
            return httpx.Response(200, json={"updates": {"updatedRows": len(body["values"]),
                                                         "updatedRange": f"{tab}!A{start}"}})
        if rest.startswith("values/") and req.method == "GET":
            tab, cells = self._split(rest[len("values/"):], sid)
            grid = bk["tabs"][tab]["grid"]
            m = re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", cells or "")
            if m:
                r0, r1 = int(m.group(2)) - 1, int(m.group(4))
                c0, _ = _cell_ref(m.group(1) + "1")
                _, c1 = _cell_ref(m.group(3) + "1")
                rows = [r[c0:c1 + 1] for r in grid[r0:r1]]
            else:
                rows = grid
            while rows and not rows[-1]:
                rows.pop()
            return httpx.Response(200, json={"values": rows})
        return httpx.Response(400, json={"error": {"message": f"unhandled {req.method} {url.path}"}})


@pytest.fixture
def gs(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.mailbox import accounts as ma
    fake = FakeSheets()
    fake.book(SID, "Sales Oct 2026", {"Customers": [
        ["Name", "City", "Due", "Status", "Salesman"],
        ["Sharma Traders", "Pune", 1500, "Pending", "Swati"],
        ["Patil Stores", "Akola", 800, "Pending", "Sandesh"],
        ["Gupta & Sons", "Pune", 2200, "Paid", "Swati"],
        ["Rao Electricals", "Nashik", 1200, "Pending", "Ankita"],
    ], "Notes": [["Note"], ["call back"]]})
    fake.book("2ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ", "Sales Sep 2026", {"Sheet1": [["A"]]})
    ma.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    from app import main
    with TestClient(main.app) as c:
        url = c.get("/api/sheets/link").json()["url"]
        assert "auth%2Fspreadsheets" in url and "state=gsh_" in url
        page = c.get("/auth/google/callback", params={"code": "c", "state": httpx.URL(url).params["state"]})
        assert page.status_code == 200 and ME in page.text
        assert c.get("/api/sheets/accounts").json()["accounts"][0]["address"] == ME
    yield fake
    ma.set_http(None)


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


def test_find_by_name_and_info(gs):
    ctx = conv_ctx()
    found = run("sheets_find", {"query": "sales"}, ctx)
    assert {s["title"] for s in found["sheets"]} == {"Sales Oct 2026", "Sales Sep 2026"}
    with pytest.raises(ToolError, match="kai sheets"):
        run("sheet_info", {"spreadsheet": "Sales"}, ctx)                   # ambiguous: asks which
    info = run("sheet_info", {"spreadsheet": "sales oct 2026"}, ctx)
    assert info["tabs"][0] == {"tab": "Customers", "columns": ["Name", "City", "Due", "Status", "Salesman"], "grid_rows": 1000}
    link = f"https://docs.google.com/spreadsheets/d/{SID}/edit#gid=0"
    assert run("sheet_read", {"spreadsheet": link, "limit": 2}, ctx)["rows"][1] == \
        {"_row": 3, "Name": "Patil Stores", "City": "Akola", "Due": 800, "Status": "Pending", "Salesman": "Sandesh"}


def test_query_is_exact(gs):
    ctx = conv_ctx()
    out = run("sheet_query", {"spreadsheet": "Sales Oct 2026", "where": [{"column": "city", "op": "=", "value": "pune"},
                                                                       {"column": "Due", "op": ">", "value": "1,000"}],
                              "totals": ["Due"]}, ctx)
    assert out["matched"] == 2 and out["totals"]["Due"]["sum"] == 3700
    g = run("sheet_query", {"spreadsheet": "Sales Oct 2026", "where": [{"column": "Status", "value": "Pending"}],
                            "group_by": "Salesman", "totals": ["Due"], "sort_by": "Due", "descending": True}, ctx)
    assert g["groups"]["Swati"] == {"count": 1, "Due": 1500} and [r["Name"] for r in g["rows"]][0] == "Sharma Traders"


def test_append_and_small_update_at_once(gs):
    ctx = conv_ctx()
    out = run("sheet_append", {"spreadsheet": "Sales Oct 2026", "rows": [{"name": "Kale Agencies", "City": "Akola", "Due": 650,
                                                                          "Status": "Pending", "Phone": "98xxxx"}],
                               "add_columns": True}, ctx)
    grid = gs.books[SID]["tabs"]["Customers"]["grid"]
    assert out["added_rows"] == 1 and out["new_columns"] == ["Phone"] and grid[0][-1] == "Phone"
    assert grid[-1][:4] == ["Kale Agencies", "Akola", 650, "Pending"] and grid[-1][-1] == "98xxxx"
    up = run("sheet_update", {"spreadsheet": "Sales Oct 2026", "where": [{"column": "Name", "value": "Sharma Traders"}],
                              "set": {"Status": "Paid"}}, ctx)
    assert up["rows"] == [2] and grid[1][3] == "Paid"
    with pytest.raises(ToolError, match="column nahi mila"):
        run("sheet_update", {"spreadsheet": "Sales Oct 2026", "rows": [3], "set": {"GSTIN": "x"}}, ctx)


def test_delete_rows_and_share_need_the_tap(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    out = run("sheet_delete_rows", {"spreadsheet": "Sales Oct 2026", "where": [{"column": "Status", "value": "Paid"}]}, ctx)
    assert out["needs_approval"]
    grid = gs.books[SID]["tabs"]["Customers"]["grid"]
    assert len(grid) == 5                                                    # nothing deleted yet
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Rows hatayein?" and "Gupta & Sons" in json.dumps(card)
    bz["svc"].decide("default", card["id"], "approve")
    assert [r[0] for r in grid] == ["Name", "Sharma Traders", "Patil Stores", "Rao Electricals"]
    from app.mailbox import contacts
    contacts.learn("default", [("Swati Sirsath", "swati@fnw.in")], 1.0, sent=True)
    run("sheet_share", {"spreadsheet": "Sales Oct 2026", "people": ["Swati"], "role": "writer"}, ctx)
    assert gs.perms == []
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert gs.perms == [{"type": "user", "role": "writer", "emailAddress": "swati@fnw.in"}]


def test_delete_refuses_if_sheet_changed(bz, gs):  # noqa: F811
    ctx = Ctx("default", bz["conv"])
    run("sheet_delete_rows", {"spreadsheet": "Sales Oct 2026", "rows": [3]}, ctx)
    gs.books[SID]["tabs"]["Customers"]["grid"].insert(1, ["New Row", "Goa", 1, "Pending", "x"])   # someone edited it
    try:
        bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    except Exception:
        pass
    assert len(gs.books[SID]["tabs"]["Customers"]["grid"]) == 6               # nothing deleted
    from app.db import SheetsPending, session
    with session() as s:
        assert s.query(SheetsPending).one().status == "failed"


def test_big_update_needs_card(bz, gs):  # noqa: F811
    grid = gs.books[SID]["tabs"]["Customers"]["grid"]
    grid.extend([[f"Cust {i}", "Pune", 100, "Pending", "Swati"] for i in range(25)])
    ctx = Ctx("default", bz["conv"])
    out = run("sheet_update", {"spreadsheet": "Sales Oct 2026", "where": [{"column": "Status", "value": "Pending"}],
                               "set": {"Status": "Reminded"}}, ctx)
    assert out["needs_approval"] and not any(r[3] == "Reminded" for r in grid)
    bz["svc"].decide("default", _events(bz["conv"], "bazar_approval")[-1]["id"], "approve")
    assert sum(1 for r in grid if r[3] == "Reminded") == 28


def test_create_import_and_export(gs, env):
    ctx = conv_ctx()
    out = run("sheet_create", {"title": "Diwali orders", "tabs": [{"name": "Orders", "header": ["Item", "Qty"],
                                                                    "rows": [{"Item": "Router", "Qty": 10}]}]}, ctx)
    assert gs.books[out["id"]]["tabs"]["Orders"]["grid"] == [["Item", "Qty"], ["Router", 10]]
    card = _events(ctx.conversation_id, "sheet")[-1]
    assert card["title"] == "Diwali orders" and card["link"].startswith("https://docs.google.com/spreadsheets/d/")
    from app.mailbox import service as ms
    f = ms.store_bytes("default", "list.csv", b"Name,Phone\nRaju,99\nSita,88\n", "mail")
    imp = run("sheet_create", {"title": "Imported", "source": {"file_id": f.id}}, ctx)
    assert gs.books[imp["id"]]["tabs"]["Sheet1"]["grid"] == [["Name", "Phone"], ["Raju", "99"], ["Sita", "88"]]
    exp = run("sheet_export", {"spreadsheet": "Sales Oct 2026"}, ctx)
    assert exp["file"] == "Sales Oct 2026.xlsx" and exp["file_id"]
    import openpyxl
    from app.db import PcFile, session
    with session() as s:
        path = s.get(PcFile, exp["file_id"]).stored_path
    wb = openpyxl.load_workbook(io.BytesIO(open(path, "rb").read()))
    assert wb.sheetnames == ["Customers", "Notes"] and wb["Customers"]["A2"].value == "Sharma Traders"
    assert _events(ctx.conversation_id, "pc_file")[-1]["name"] == "Sales Oct 2026.xlsx"


def test_not_connected(env):
    with pytest.raises(ToolError, match="Profile > Google Sheets"):
        run("sheet_query", {"spreadsheet": "x"}, Ctx("someone", "c"))
