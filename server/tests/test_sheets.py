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
        # v0.210 tracking
        self.clears = []            # list of [sid, ranges]
        self.copy_tabs = []         # list of (sid, sheet_id, dest_sid, new_title)
        self.batch_log = []         # every batchUpdate request (full body)
        self.protects = []          # [(sid, tab_id, range, editors)]
        self.named_ranges = {}     # sid -> [{"name":..., "range":..., "namedRangeId":...}]
        self.cf_rules = {}         # sid -> list of rules added
        self.validations = {}      # sid -> list of validation rules
        self.merges = []           # [(sid, tab_id, range, merge_type)]
        self.unmerges = []
        self.notes_set = []        # [(sid, tab_id, row, col, note)]
        self.find_replace_calls = []  # [(sid, find, replace, allSheets, sheetId)]

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
        # ---- GET meta OR sheets-with-data (for cell_notes read_only) ----
        if not rest and not action and req.method == "GET":
            fields = url.params.get("fields", "")
            sheets_out = []
            for name, t in bk["tabs"].items():
                props = {"sheetId": t["id"], "title": name, "index": t["id"],
                         "gridProperties": {"rowCount": 1000, "columnCount": 26}}
                sh: dict = {"properties": props}
                if "data(" in fields:
                    # build rowData from the grid so cell_notes can read notes; we return no notes (empty)
                    row_data = []
                    for ri, row in enumerate(t["grid"]):
                        vals = []
                        for v in row:
                            vals.append({"userEnteredValue": str(v) if v != "" else None})
                        row_data.append({"values": vals})
                    sh["data"] = [{"rowData": row_data}] if row_data else []
                sheets_out.append(sh)
            return httpx.Response(200, json={"spreadsheetId": sid, "properties": {"title": bk["title"]},
                                             "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{sid}/edit",
                                             "sheets": sheets_out,
                                             "namedRanges": self.named_ranges.get(sid, [])})
        # ---- copyTo: POST /sheets/{sheet_id}:copyTo ----
        if rest.startswith("sheets/") and rest.endswith(":copyTo") and req.method == "POST":
            sheet_id = int(rest.split("/")[1].split(":")[0])
            dest_sid = body["destination_spreadsheet_id"]
            new_title = body.get("newTitle") or "Copy"
            self.copy_tabs.append((sid, sheet_id, dest_sid, new_title))
            return httpx.Response(200, json={"sheetId": 9999, "title": new_title,
                                             "spreadsheetId": dest_sid})
        # ---- values:batchClear ----
        if rest == "values:batchClear":
            self.clears.append((sid, list(body.get("ranges", []))))
            return httpx.Response(200, json={})
        if action == "batchUpdate":
            self.batch_log.append((sid, body["requests"]))
            replies = []
            for r in body["requests"]:
                rep: dict = {}
                if "deleteDimension" in r:
                    rg = r["deleteDimension"]["range"]
                    tab = next(t for t in bk["tabs"].values() if t["id"] == rg["sheetId"])
                    del tab["grid"][rg["startIndex"]:rg["endIndex"]]
                if "addSheet" in r:
                    name = r["addSheet"]["properties"]["title"]
                    bk["tabs"][name] = {"id": len(bk["tabs"]), "grid": []}
                    rep["addSheet"] = {"properties": {"sheetId": bk["tabs"][name]["id"], "title": name}}
                if "duplicateSheet" in r:
                    src_id = r["duplicateSheet"]["sourceSheetId"]
                    new_name = r["duplicateSheet"]["newSheetName"]
                    src_tab = next((n, t) for n, t in bk["tabs"].items() if t["id"] == src_id)
                    new_id = max(t["id"] for t in bk["tabs"].values()) + 1
                    bk["tabs"][new_name] = {"id": new_id, "grid": [list(r) for r in src_tab[1]["grid"]]}
                    rep["duplicateSheet"] = {"newSheetId": new_id, "title": new_name}
                if "deleteSheet" in r:
                    tid = r["deleteSheet"]["sheetId"]
                    name = next(n for n, t in bk["tabs"].items() if t["id"] == tid)
                    del bk["tabs"][name]
                    rep["deleteSheet"] = {"sheetId": tid}
                if "repeatCell" in r:
                    pass  # format applied; FakeSheets doesn't model cell formatting
                if "updateSheetProperties" in r:
                    pass  # freeze; FakeSheets ignores
                if "addProtectedRange" in r:
                    pr = r["addProtectedRange"]["protectedRange"]
                    self.protects.append((sid, pr["range"]["sheetId"], pr["range"],
                                          pr.get("editors", {}).get("users", [])))
                if "addNamedRange" in r:
                    nr = r["addNamedRange"]["namedRange"]
                    rng = self.named_ranges.setdefault(sid, [])
                    nr_id = str(len(rng) + 1)   # real API uses numeric strings as IDs
                    stored = {"namedRangeId": nr_id, "name": nr["name"], "range": nr["range"]}
                    rng.append(stored)
                    rep["addNamedRange"] = {"namedRange": stored}
                if "updateNamedRange" in r:
                    nr = r["updateNamedRange"]["namedRange"]
                    for stored in self.named_ranges.get(sid, []):
                        if stored["namedRangeId"] == nr.get("namedRangeId"):
                            stored.update({k: v for k, v in nr.items() if k != "namedRangeId"})
                if "deleteNamedRange" in r:
                    nrid = r["deleteNamedRange"]["namedRangeId"]
                    self.named_ranges[sid] = [n for n in self.named_ranges.get(sid, []) if n["namedRangeId"] != nrid]
                if "addConditionalFormatRule" in r:
                    self.cf_rules.setdefault(sid, []).append(r["addConditionalFormatRule"])
                if "updateConditionalFormatRule" in r:
                    pass
                if "deleteConditionalFormatRule" in r:
                    pass
                if "setDataValidation" in r:
                    self.validations.setdefault(sid, []).append(r["setDataValidation"])
                if "mergeCells" in r:
                    self.merges.append((sid, r["mergeCells"]["range"]["sheetId"],
                                         r["mergeCells"]["range"], r["mergeCells"]["mergeType"]))
                if "unmergeCells" in r:
                    self.unmerges.append((sid, r["unmergeCells"]["range"]["sheetId"], r["unmergeCells"]["range"]))
                if "updateCells" in r:
                    start = r["updateCells"]["start"]
                    for row in r["updateCells"].get("rows", []):
                        for ci, cell in enumerate(row.get("values", [])):
                            if "note" in cell and cell["note"]:
                                self.notes_set.append((sid, start["sheetId"],
                                                       start["rowIndex"] + 1, start["columnIndex"] + ci + 1,
                                                       cell["note"]))
                if "findReplace" in r:
                    fr = r["findReplace"]
                    self.find_replace_calls.append((sid, fr.get("find"), fr.get("replacement"),
                                                    fr.get("allSheets"), fr.get("sheetId")))
                    rep["findReplace"] = {"valuesChanged": 3, "formulasChanged": 0,
                                          "rowsChanged": 2, "sheetsChanged": 1}
                replies.append(rep)
            return httpx.Response(200, json={"replies": replies})
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


# ---- v0.210.0 Google Sheets 100% coverage: 12 new tools (clear, copy_tab, duplicate_tab,
# delete_tab, format, protect, named_range, conditional_format, data_validation, merge,
# notes, find_replace) ----

def test_clear_card_flow(bz, gs):  # noqa: F811
    """sheet_clear creates a confirm card; approve clears the ranges."""
    ctx = Ctx("default", bz["conv"])
    # pre-populate some data
    gs.books[SID]["tabs"]["Customers"]["grid"][1][1] = "Pune"
    out = run("sheet_clear", {"spreadsheet": "Sales Oct 2026", "ranges": ["A2:C3"]}, ctx)
    assert out["needs_approval"]
    assert gs.clears == []     # nothing cleared yet
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Values saaf karein?"
    bz["svc"].decide("default", card["id"], "approve")
    assert gs.clears == [(SID, ["'Customers'!A2:C3"])]    # q_tab() quotes the tab name


def test_copy_tab_to_another(gs, env):
    """sheet_copy_tab copies a tab to another spreadsheet; returns new tab id."""
    ctx = conv_ctx()
    out = run("sheet_copy_tab", {"spreadsheet": "Sales Oct 2026", "tab": "Customers",
                                  "dest_spreadsheet": "Sales Sep 2026", "new_title": "Cust Copy"}, ctx)
    assert out["src_tab"] == "Customers" and out["new_tab"] == "Cust Copy"
    assert out["dest_spreadsheet_id"] == "2ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
    assert out["new_sheet_id"] == 9999     # FakeSheets returns a fixed new sheetId for copyTo
    assert gs.copy_tabs and gs.copy_tabs[0][0] == SID and gs.copy_tabs[0][2] == "2ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"


def test_duplicate_tab_in_same_sheet(gs):
    """sheet_duplicate_tab creates a new tab inside the same spreadsheet."""
    ctx = conv_ctx()
    out = run("sheet_duplicate_tab", {"spreadsheet": "Sales Oct 2026", "tab": "Customers",
                                       "new_title": "Customers Backup"}, ctx)
    assert out["src_tab"] == "Customers" and out["new_tab"] == "Customers Backup"
    # the FakeSheets batchUpdate handler for duplicateSheet copies the grid into a new tab name
    assert "Customers Backup" in gs.books[SID]["tabs"]
    # the new tab should have the same grid as the source
    assert gs.books[SID]["tabs"]["Customers Backup"]["grid"][0] == ["Name", "City", "Due", "Status", "Salesman"]


def test_delete_tab_card_flow(bz, gs):  # noqa: F811
    """sheet_delete_tab shows a confirm card; approve deletes the tab."""
    ctx = Ctx("default", bz["conv"])
    out = run("sheet_delete_tab", {"spreadsheet": "Sales Oct 2026", "tab": "Notes"}, ctx)
    assert out["needs_approval"]
    assert "Notes" in gs.books[SID]["tabs"]    # nothing deleted yet
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Tab hatayein?"
    bz["svc"].decide("default", card["id"], "approve")
    assert "Notes" not in gs.books[SID]["tabs"]


def test_delete_tab_refuses_on_last_tab(bz, gs):  # noqa: F811
    """The last tab can't be deleted."""
    ctx = Ctx("default", bz["conv"])
    # delete every tab except Notes
    for n in list(gs.books[SID]["tabs"]):
        if n != "Notes":
            del gs.books[SID]["tabs"][n]
    with pytest.raises(ToolError, match="akhaari tab"):
        run("sheet_delete_tab", {"spreadsheet": "Sales Oct 2026", "tab": "Notes"}, ctx)


def test_format_cells_bold_and_freeze(gs):
    """sheet_format applies bold + bg_color + freeze rows via batchUpdate."""
    ctx = conv_ctx()
    out = run("sheet_format", {"spreadsheet": "Sales Oct 2026", "range": "A1:F1",
                                 "format": {"bold": True, "bg_color": "lightblue", "freeze_rows": 2}}, ctx)
    assert out["range"] == "A1:F1"
    assert "bold" in out["applied"] and "bg_color" in out["applied"] and "freeze_rows" in out["applied"]
    # batchUpdate should have been called with repeatCell + updateSheetProperties
    sid, reqs = gs.batch_log[-1]
    kinds = [next(iter(r)) for r in reqs]
    assert "repeatCell" in kinds and "updateSheetProperties" in kinds


def test_protect_card_with_editors(bz, gs):  # noqa: F811
    """sheet_protect shows a card; approve locks the range with the listed editors."""
    ctx = Ctx("default", bz["conv"])
    out = run("sheet_protect", {"spreadsheet": "Sales Oct 2026", "range": "A1:C10",
                                  "editors": ["swati@fnw.in", "sandesh@fnw.in"], "description": "locked totals"}, ctx)
    assert out["needs_approval"]
    assert gs.protects == []     # not locked yet
    card = _events(bz["conv"], "bazar_approval")[-1]
    assert card["title"] == "Lock kar dein?"
    bz["svc"].decide("default", card["id"], "approve")
    assert len(gs.protects) == 1
    sid, tab_id, rng, editors = gs.protects[0]
    assert sid == SID and set(editors) == {"swati@fnw.in", "sandesh@fnw.in"}
    assert rng["sheetId"] == tab_id and rng["startRowIndex"] == 0 and rng["endRowIndex"] == 10


def test_named_range_lifecycle(gs):
    """sheet_named_range add / list / delete."""
    ctx = conv_ctx()
    # add
    add = run("sheet_named_range", {"spreadsheet": "Sales Oct 2026", "action": "add",
                                      "name": "Revenue", "range": "B1:B100", "tab": "Customers"}, ctx)
    assert add["action"] == "added" and add["name"] == "Revenue"
    assert add["range"] == "Customers!B1:B100"
    # list
    lst = run("sheet_named_range", {"spreadsheet": "Sales Oct 2026", "action": "list"}, ctx)
    assert any(nr["name"] == "Revenue" for nr in lst["named_ranges"])
    # delete
    nr_id = lst["named_ranges"][0]["namedRangeId"]
    dl = run("sheet_named_range", {"spreadsheet": "Sales Oct 2026", "action": "delete",
                                     "named_id": int(nr_id.replace("nr", ""))}, ctx)
    assert dl["action"] == "deleted"
    lst2 = run("sheet_named_range", {"spreadsheet": "Sales Oct 2026", "action": "list"}, ctx)
    assert not any(nr["name"] == "Revenue" for nr in lst2["named_ranges"])


def test_conditional_format_color_scale(gs):
    """sheet_conditional_format with a color_scale rule."""
    ctx = conv_ctx()
    out = run("sheet_conditional_format", {"spreadsheet": "Sales Oct 2026", "range": "C2:C10",
                                              "rule": {"type": "color_scale",
                                                        "min": {"color": "red", "type": "min"},
                                                        "max": {"color": "green", "type": "max"}}}, ctx)
    assert out["rule_type"] == "color_scale" and out["action"] == "added"
    sid, reqs = gs.batch_log[-1]
    rule = reqs[0]["addConditionalFormatRule"]["rule"]
    assert "gradientRule" in rule
    assert rule["gradientRule"]["minpoint"]["color"] == {"red": 1.0, "green": 0.0, "blue": 0.0}
    assert rule["gradientRule"]["maxpoint"]["color"] == {"red": 0.0, "green": 1.0, "blue": 0.0}


def test_conditional_format_expression(gs):
    """sheet_conditional_format with an expression rule."""
    ctx = conv_ctx()
    out = run("sheet_conditional_format", {"spreadsheet": "Sales Oct 2026", "range": "C2:C10",
                                              "rule": {"type": "expression", "formula": "=C2>1000",
                                                        "format": {"bg_color": "lightyellow"}}}, ctx)
    assert out["rule_type"] == "expression"
    sid, reqs = gs.batch_log[-1]
    rule = reqs[0]["addConditionalFormatRule"]["rule"]
    assert rule["booleanRule"]["condition"]["type"] == "CUSTOM_FORMULA"
    assert rule["booleanRule"]["condition"]["values"][0]["userEnteredValue"] == "C2>1000"


def test_data_validation_list(gs):
    """sheet_data_validation with a list validation (dropdown)."""
    ctx = conv_ctx()
    out = run("sheet_data_validation", {"spreadsheet": "Sales Oct 2026", "range": "D2:D100",
                                          "rule": {"type": "list", "values": ["Paid", "Pending", "Cancelled"],
                                                    "show_dropdown": True, "strict": False}}, ctx)
    assert out["validation_type"] == "list" and out["action"] == "set"
    sid, reqs = gs.batch_log[-1]
    dv = reqs[0]["setDataValidation"]["rule"]
    assert dv["condition"]["type"] == "ONE_OF_LIST"
    assert dv["condition"]["values"][0]["userEnteredValue"] == "Paid,Pending,Cancelled"
    assert dv["showCustomUi"] is True and dv["strict"] is False


def test_merge_and_unmerge(gs):
    """sheet_merge + sheet_merge action=unmerge."""
    ctx = conv_ctx()
    out = run("sheet_merge", {"spreadsheet": "Sales Oct 2026", "range": "A1:C1",
                                "merge_type": "MERGE_ALL"}, ctx)
    assert out["action"] == "merged" and out["merge_type"] == "MERGE_ALL"
    assert len(gs.merges) == 1 and gs.merges[0][3] == "MERGE_ALL"
    out2 = run("sheet_merge", {"spreadsheet": "Sales Oct 2026", "range": "A1:C1", "action": "unmerge"}, ctx)
    assert out2["action"] == "unmerged"
    assert len(gs.unmerges) == 1


def test_notes_set_and_pii_guard(gs):
    """sheet_notes sets cell notes; refuses PII text."""
    ctx = conv_ctx()
    out = run("sheet_notes", {"spreadsheet": "Sales Oct 2026", "tab": "Customers",
                                "notes": [{"row": 2, "col": 5, "note": "follow up next week"}]}, ctx)
    assert out["notes_set"] == 1
    assert len(gs.notes_set) == 1
    sid, tab_id, row, col, note = gs.notes_set[0]
    assert row == 2 and col == 5 and "follow up" in note
    # PII guard refuses Aadhaar in note text
    with pytest.raises(ToolError, match="personal"):
        run("sheet_notes", {"spreadsheet": "Sales Oct 2026", "tab": "Customers",
                             "notes": [{"row": 2, "col": 5, "note": "Aadhaar 2342 3456 7890"}]}, ctx)


def test_find_replace_counts_and_pii_guard(gs):
    """sheet_find_replace returns counts; refuses PII in replacement text."""
    ctx = conv_ctx()
    out = run("sheet_find_replace", {"spreadsheet": "Sales Oct 2026", "tab": "Customers",
                                       "find": "Pune", "replace": "Mumbai"}, ctx)
    assert out["values_changed"] == 3 and out["sheets_changed"] == 1
    assert len(gs.find_replace_calls) == 1
    # PII guard refuses Aadhaar in replacement text
    with pytest.raises(ToolError, match="personal"):
        run("sheet_find_replace", {"spreadsheet": "Sales Oct 2026", "tab": "Customers",
                                     "find": "x", "replace": "Aadhaar 2342 3456 7890"}, ctx)
