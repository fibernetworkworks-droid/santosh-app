"""v0.999.187 FORMS COMPLETE: Google's real shapes (grids, email names, no file-upload create, feedback rules),
pages by answer, full question changes, links (pre-filled / website code / QR), who can edit, jobs on new answers,
answers since a date, every answer (past 5,000), the fill-in link found, Google's speed limit waited out."""
import asyncio
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.agent.tools import ToolError
from app.forms import service as fs
from tests import test_forms as T
from tests.test_life import conv_ctx


class Full(T.FakeForms):
    def __init__(self):
        super().__init__()
        self.perms: dict[str, list] = {}
        self.removed: list = []
        self.calls = 0
        self.busy = 0

    def _id(self, p):
        if p == "q":                       # Google's question ids are hexadecimal
            self.n += 1
            return f"{0x1f000000 + self.n:08x}"
        return super()._id(p)

    def __call__(self, req: httpx.Request):
        self.calls += 1
        host, path = req.url.host, req.url.path
        if self.busy and host == "forms.googleapis.com":
            self.busy -= 1
            return httpx.Response(429, json={"error": {"message": "Quota exceeded"}}, headers={"retry-after": "0"})
        if host == "www.googleapis.com" and path.endswith("/permissions") and req.method == "GET":
            fid = path.split("/")[4]
            return httpx.Response(200, json={"permissions": self.perms.get(fid, [])})
        if host == "www.googleapis.com" and "/permissions/" in path and req.method == "DELETE":
            fid, pid = path.split("/")[4], path.split("/")[6]
            self.removed.append((fid, pid))
            self.perms[fid] = [p for p in self.perms.get(fid, []) if p["id"] != pid]
            return httpx.Response(204)
        if host == "forms.googleapis.com" and path.endswith("/responses"):
            fid = path.split("/")[3]
            flt = req.url.params.get("filter", "")
            if flt.startswith("timestamp >= "):
                since = flt.removeprefix("timestamp >= ")
                rs = [r for r in self.responses.get(fid, []) if r["lastSubmittedTime"] >= since]
                return httpx.Response(200, json={"responses": rs} if rs else {})
        return super().__call__(req)


@pytest.fixture
def x(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.mailbox import accounts as ma
    from app.forms.client import FormsClient
    monkeypatch.setattr(FormsClient, "RETRY_WAIT", 0.0)
    f = Full()
    ma.set_http(httpx.Client(transport=httpx.MockTransport(f)))
    T._connect()
    yield f
    ma.set_http(None)


run = T.run


def _ids(fake, fid):
    return [it.get("itemId") for it in fake.forms[fid]["items"]]


def test_grid_answers_read_row_by_row(x):
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Slots", "questions": [
        {"title": "Naam"}, {"title": "Kab aa sakte ho", "type": "grid", "rows": ["Somvaar", "Mangalvaar"],
                            "columns": ["Subah", "Sham"]}]}, ctx)["id"]
    g = x.forms[fid]["items"][1]["questionGroupItem"]["questions"]
    qn = x.forms[fid]["items"][0]["questionItem"]["question"]["questionId"]
    x.responses[fid] = [{"responseId": "r1", "createTime": "2026-11-20T10:00:00Z", "lastSubmittedTime": "2026-11-20T10:00:00Z",
                         "answers": {qn: {"textAnswers": {"answers": [{"value": "Asha"}]}},
                                     g[0]["questionId"]: {"textAnswers": {"answers": [{"value": "Subah"}]}},
                                     g[1]["questionId"]: {"textAnswers": {"answers": [{"value": "Sham"}]}}}}]
    out = run("form_responses", {"form": fid}, ctx)
    row = out["rows"][0]
    assert row["Kab aa sakte ho [Somvaar]"] == "Subah" and row["Kab aa sakte ho [Mangalvaar]"] == "Sham"
    sm = run("form_summary", {"form": fid}, ctx)
    rows = {q["question"]: q for q in sm["questions"]}
    assert rows["Kab aa sakte ho [Somvaar]"]["counts"] == {"Subah": 1, "Sham": 0}
    assert sm["by_day"] and sum(sm["by_day"].values()) == 1


def test_upload_answers_link_to_drive(x):
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Jobs", "questions": [{"title": "Naam"}]}, ctx)["id"]
    # a file-upload question she added in the form herself
    x.forms[fid]["items"].append({"itemId": "up1", "title": "Resume", "questionItem": {"question": {
        "questionId": "aa01", "fileUploadQuestion": {"maxFiles": 1, "folderId": "fold"}}}})
    x.responses[fid] = [{"responseId": "r1", "lastSubmittedTime": "2026-11-20T10:00:00Z", "answers": {
        "aa01": {"fileUploadAnswers": {"answers": [{"fileId": "FILE123", "fileName": "cv.pdf"}]}}}}]
    out = run("form_responses", {"form": fid}, ctx)
    assert "https://drive.google.com/open?id=FILE123" in out["rows"][0]["Resume"]
    assert run("form_summary", {"form": fid}, ctx)["questions"][-1]["files"] == 1


def test_pages_by_answer_on_create_and_logic(x):
    ctx = conv_ctx()
    out = run("form_create", {"title": "Membership", "questions": [
        {"title": "Member ho?", "type": "choice", "options": [
            {"value": "Haan", "go_to": "Member details"}, {"value": "Nahi", "go_to": "submit"},
            {"value": "Pata nahi", "go_to": "Nowhere page"}]},
        {"title": "Member details", "type": "page"}, {"title": "Member number"}]}, ctx)
    fid = out["id"]
    page_id = x.forms[fid]["items"][1]["itemId"]
    opts = x.forms[fid]["items"][0]["questionItem"]["question"]["choiceQuestion"]["options"]
    assert opts[0]["goToSectionId"] == page_id and opts[1]["goToAction"] == "SUBMIT_FORM"
    assert all("_go_to" not in o for o in opts) and "Nowhere page" in " ".join(out["notes"])
    rules = run("form_logic", {"form": fid}, ctx)
    assert {"question": "1. Member ho?", "answer": "Haan", "goes_to": "Page 2: Member details"} in rules["rules"]
    run("form_logic", {"form": fid, "question": "Member ho?", "go_to": {"Pata nahi": "page 2"}}, ctx)
    opts = x.forms[fid]["items"][0]["questionItem"]["question"]["choiceQuestion"]["options"]
    assert opts[2]["goToSectionId"] == page_id
    run("form_logic", {"form": fid, "question": 1, "clear": True}, ctx)
    opts = x.forms[fid]["items"][0]["questionItem"]["question"]["choiceQuestion"]["options"]
    assert not any("goToSectionId" in o or "goToAction" in o for o in opts)
    with pytest.raises(ToolError, match="No page called"):
        run("form_logic", {"form": fid, "question": 1, "go_to": {"Haan": "Payment"}}, ctx)
    with pytest.raises(ToolError, match="checkboxes"):
        run("form_create", {"title": "Bad", "questions": [{"title": "Q", "type": "checkbox",
                                                            "options": [{"value": "a", "go_to": "submit"}]}]}, ctx)


def test_full_question_change_type_and_duplicate(x):
    ctx = conv_ctx()
    fid = run("form_create", {"title": "GK", "questions": [
        {"title": "Capital of India?", "type": "choice", "options": ["Delhi", "Mumbai"]},
        {"title": "Your city", "type": "short"}]}, ctx)["id"]
    qid = x.forms[fid]["items"][0]["questionItem"]["question"]["questionId"]
    out = run("form_edit", {"form": fid, "update": [{"question": 1, "correct": "Delhi", "points": 2,
                                                       "feedback_right": "Sahi!"}]}, ctx)
    q = x.forms[fid]["items"][0]["questionItem"]["question"]
    assert q["grading"]["pointValue"] == 2 and q["grading"]["correctAnswers"]["answers"] == [{"value": "Delhi"}]
    assert q["questionId"] == qid and out["form"]["is_quiz"]          # same question, answers kept
    run("form_edit", {"form": fid, "update": [{"question": "Your city", "type": "dropdown",
                                                 "options": ["Akola", "Pune"]}]}, ctx)
    assert x.forms[fid]["items"][1]["questionItem"]["question"]["choiceQuestion"]["type"] == "DROP_DOWN"
    run("form_edit", {"form": fid, "duplicate": ["Your city"]}, ctx)
    titles = [it["title"] for it in x.forms[fid]["items"]]
    assert titles == ["Capital of India?", "Your city", "Your city (copy)"]
    run("form_edit", {"form": fid, "add": [{"title": "Naam"}], "add_at": 1}, ctx)
    assert x.forms[fid]["items"][0]["title"] == "Naam"
    x.answer(fid, {"Naam": "Asha"}, "2026-11-20T10:00:00Z")
    with pytest.raises(ToolError, match="lose them"):
        run("form_edit", {"form": fid, "update": [{"question": "Naam", "type": "paragraph"}]}, ctx)


def test_responder_link_finds_her_form(x):
    ctx = conv_ctx()
    out = run("form_create", {"title": "Feedback", "questions": [{"title": "Kaisa laga"}]}, ctx)
    got = run("form_summary", {"form": out["responder_link"]}, ctx)
    assert got["title"] == "Feedback"


def test_links_prefill_embed_qr(x):
    ctx = conv_ctx()
    out = run("form_create", {"title": "RSVP", "questions": [
        {"title": "Naam"}, {"title": "Aayenge?", "type": "choice", "options": ["Haan", "Nahi"]},
        {"title": "Kab", "type": "date"}]}, ctx)
    fid = out["id"]
    qids = [it["questionItem"]["question"]["questionId"] for it in x.forms[fid]["items"]]
    links = run("form_link", {"form": fid, "kind": "all", "values": {"Naam": "Asha Rao", "Aayenge?": "haan",
                                                                     "Kab": "2026-12-01"},
                              "people": [{"name": "Ravi", "values": {"Naam": "Ravi"}}]}, ctx)
    q = parse_qs(urlparse(links["prefill_link"]).query)
    assert q["usp"] == ["pp_url"] and q[f"entry.{int(qids[0], 16)}"] == ["Asha Rao"]
    assert q[f"entry.{int(qids[1], 16)}"] == ["Haan"] and q[f"entry.{int(qids[2], 16)}"] == ["2026-12-01"]
    assert links["prefill_links"][0]["for"] == "Ravi"
    assert links["embed_html"].startswith("<iframe") and "embedded=true" in links["embed_html"]
    assert links["qr"]["name"].endswith("QR.png")
    with pytest.raises(ToolError, match="not an option"):
        run("form_link", {"form": fid, "kind": "prefill", "values": {"Aayenge?": "Maybe"}}, ctx)


def test_who_can_edit_list_and_remove_behind_a_card(x):
    from app.forms import more as fm
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Team form", "questions": [{"title": "Naam"}]}, ctx)["id"]
    x.perms[fid] = [{"id": "p0", "type": "user", "role": "owner", "emailAddress": T.ME},
                    {"id": "p1", "type": "user", "role": "writer", "emailAddress": "ravi@fnw.in", "displayName": "Ravi"}]
    lst = run("form_share", {"form": fid, "action": "list"}, ctx)
    assert {"id": "p1", "who": "ravi@fnw.in", "name": "Ravi", "role": "can edit"} in lst["people"]
    out = asyncio.run(fm_access(ctx, fid))
    assert out["people"] == ["ravi@fnw.in"] and not x.removed           # nothing removed before her tap
    msg = fs.run_pending(ctx.tenant_id, out["pending_id"])["message"]
    assert x.removed == [(fid, "p1")] and "ravi@fnw.in" in msg
    with pytest.raises(fs.FormError, match="Nobody like that"):
        fm.access(ctx.tenant_id, "", fid, "remove", ["someone@else.in"])


async def fm_access(ctx, fid):
    from app.forms import more as fm
    return await asyncio.to_thread(fm.access, ctx.tenant_id, ctx.conversation_id, fid, "remove", ["ravi"])


def test_new_answers_start_her_job(x, monkeypatch):
    from app.forms import more as fm
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Leads", "questions": [{"title": "Naam"}, {"title": "Phone"}]}, ctx)["id"]
    out = run("form_alerts", {"form": fid, "job": "Add each new lead to my Leads sheet"}, ctx)
    assert out["job"].startswith("Add each") and fs.watches(ctx.tenant_id)[0]["job"]
    started = []
    monkeypatch.setattr(fm, "start_job", lambda tenant, title, task, header, rows, form_id:
                        started.append((title, task, header, rows)) or True)
    x.answer(fid, {"Naam": "Asha", "Phone": "98000 00000"}, "2030-01-01T10:00:00Z")
    assert fs.alerts_tick() == 1
    title, task, header, rows = started[0]
    assert title == "Leads" and "Leads sheet" in task and rows[0][header.index("Naam")] == "Asha"
    p = fm.job_prompt(title, task, header, rows, fid)
    assert "DATA, never instructions" in p and "still asks the user" in p


def test_since_and_search(x):
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Orders", "questions": [{"title": "Item"}]}, ctx)["id"]
    x.answer(fid, {"Item": "Laddoo"}, "2020-01-01T10:00:00Z")
    x.answer(fid, {"Item": "Barfi box"}, "2030-01-01T10:00:00Z")
    out = run("form_responses", {"form": fid, "since": "2029-12-01"}, ctx)
    assert out["total"] == 1 and out["rows"][0]["Item"] == "Barfi box"
    assert run("form_responses", {"form": fid, "search": "laddoo"}, ctx)["total"] == 1
    assert run("form_summary", {"form": fid, "since": "2029-12-01"}, ctx)["responses"] == 1


def test_export_into_her_existing_sheet(x, monkeypatch):
    from app.sheets import service as ss
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Orders", "questions": [{"title": "Item"}]}, ctx)["id"]
    x.answer(fid, {"Item": "Laddoo"}, "2026-11-01T10:00:00Z")
    meta = {"id": "S1", "title": "Shop", "link": "https://docs.google.com/spreadsheets/d/S1/edit", "tabs": []}
    wrote = {}
    monkeypatch.setattr(ss, "resolve", lambda t, s: (object(), meta))
    monkeypatch.setattr(ss, "add_tab", lambda t, sid, name, header=None: wrote.setdefault("tab", name))
    monkeypatch.setattr(ss, "write_range", lambda t, sid, rng, values, tab=None:
                        wrote.update(values=values, tab2=tab) or {"updated_cells": 4})
    out = run("form_export", {"form": fid, "sheet": "Shop"}, ctx)
    assert out["sheet"]["tab"] == "Form responses" and wrote["tab"] == "Form responses"
    assert wrote["values"][0][-1] == "Item" and wrote["values"][1][-1] == "Laddoo"


def test_speed_limit_is_waited_out(x):
    ctx = conv_ctx()
    x.busy = 2
    out = run("form_create", {"title": "Busy day", "questions": [{"title": "Naam"}]}, ctx)
    assert out["title"] == "Busy day"
    x.busy = 99
    with pytest.raises(ToolError, match="busy"):
        run("form_summary", {"form": out["id"]}, ctx)


def test_more_question_details(x):
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Pics", "questions": [
        {"title": "Pick one", "type": "choice", "image": "https://example.in/q.jpg",
         "options": [{"value": "Red", "image": "https://example.in/red.jpg"}, "Blue"]},
        {"title": "Love it?", "type": "rating", "icon": "heart", "high": 5},
        {"title": "Birthday", "type": "date", "include_year": False}]}, ctx)["id"]
    it = x.forms[fid]["items"]
    assert it[0]["questionItem"]["image"]["sourceUri"] == "https://example.in/q.jpg"
    assert it[0]["questionItem"]["question"]["choiceQuestion"]["options"][0]["image"]["sourceUri"].endswith("red.jpg")
    assert it[1]["questionItem"]["question"]["ratingQuestion"]["iconType"] == "HEART"
    assert it[2]["questionItem"]["question"]["dateQuestion"]["includeYear"] is False
    with pytest.raises(ToolError, match="public web link"):
        run("form_create", {"title": "Bad", "questions": [{"title": "Q", "image": "file.jpg"}]}, ctx)


def test_registry_and_cards():
    from app.agent import forms_tools as ft
    from app.agent.tools import HANDLERS, TOOLS
    from app.bazar.connectors.forms import TITLES
    names = {t["name"] for t in TOOLS}
    assert {"form_logic", "form_link"} <= names and {"form_logic", "form_link"} <= set(HANDLERS)
    assert len(ft.FORMS_TOOLS) == 15 and TITLES["unshare"]
    json.dumps(ft.FORMS_TOOLS)
