"""Google Forms: connecting by Google sign-in, making forms and quizzes, editing, answers, summary, export,
open / close, sharing and deleting answered questions behind confirm cards, new-answer alerts."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

import app.forms.models  # noqa: F401  (tables)
from app.agent import forms_tools as ft
from app.agent.tools import Ctx, ToolError
from tests.test_life import conv_ctx

ME = "meghana@fnw.in"


class FakeForms:
    """Google Forms API v1 + Drive files/permissions + Google token/userinfo, in memory."""

    def __init__(self):
        self.forms: dict[str, dict] = {}
        self.responses: dict[str, list] = {}
        self.shares: list = []
        self.batches: list = []
        self.n = 0
        self.trashed: list = []        # v0.213: form ids sent to Drive Trash
        self.copies: list = []         # v0.213: (src_id, new_title)
        self.single_response_gets: list = []   # v0.213: (form_id, response_id)

    def _id(self, p):
        self.n += 1
        return f"{p}{self.n:04d}" + "x" * 30

    def __call__(self, req: httpx.Request):
        host, path, params = req.url.host, req.url.path, req.url.params
        if host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "at", "refresh_token": "rt", "expires_in": 3600,
                                             "scope": "openid email https://www.googleapis.com/auth/forms.body "
                                                      "https://www.googleapis.com/auth/forms.responses.readonly"})
        if host == "openidconnect.googleapis.com":
            return httpx.Response(200, json={"email": ME, "name": "Meghana"})
        assert req.headers["authorization"] == "Bearer at"
        body = json.loads(req.content) if req.content else {}
        if host == "www.googleapis.com" and path == "/drive/v3/files":
            q = params["q"]
            name = q.split("name contains '")[1].split("'")[0] if "name contains" in q else ""
            files = [{"id": f["formId"], "name": f["info"]["title"], "modifiedTime": "2026-10-19T10:00:00Z"}
                     for f in self.forms.values() if name.lower() in f["info"]["title"].lower()]
            return httpx.Response(200, json={"files": files})
        if host == "www.googleapis.com" and path.endswith("/permissions"):
            self.shares.append((path.split("/")[4], body, dict(params)))
            return httpx.Response(200, json={"id": "perm1"})
        # v0.213: Drive trash + copy for forms
        if host == "www.googleapis.com" and req.method == "PATCH" and path.startswith("/drive/v3/files/"):
            fid = path.split("/")[4]
            if body.get("trashed"):
                self.trashed.append(fid)
            return httpx.Response(200, json={"id": fid, "trashed": True})
        if host == "www.googleapis.com" and req.method == "POST" and path.endswith("/copy"):
            src = path.split("/")[4]
            title = body.get("name") or (self.forms[src]["info"]["title"] + " copy")
            nf = {"formId": self._id("f"), "info": {"title": title, "documentTitle": title},
                  "items": json.loads(json.dumps(self.forms[src]["items"])), "settings": json.loads(json.dumps(self.forms[src].get("settings", {}))),
                  "responderUri": "", "publishSettings": {"publishState": {"isPublished": False, "isAcceptingResponses": False}}}
            for it in nf["items"]:
                it["itemId"] = self._id("i")[:8]
                if "questionItem" in it:
                    it["questionItem"]["question"]["questionId"] = self._id("q")[:8]
                if "questionGroupItem" in it and "question" in it["questionGroupItem"]:
                    it["questionGroupItem"]["question"]["questionId"] = self._id("q")[:8]
            self.forms[nf["formId"]] = nf
            self.copies.append((src, title))
            return httpx.Response(200, json={"id": nf["formId"], "name": title, "mimeType": "application/vnd.google-apps.form"})
        assert host == "forms.googleapis.com"
        p = path.removeprefix("/v1/forms")
        if p == "" and req.method == "POST":
            fid = self._id("f")
            assert set(body["info"]) <= {"title", "documentTitle"}       # create accepts only the title
            self.forms[fid] = {"formId": fid, "info": dict(body["info"]), "items": [], "settings": {},
                               "responderUri": f"https://docs.google.com/forms/d/e/{fid}R/viewform",
                               "publishSettings": {"publishState": {"isPublished": False, "isAcceptingResponses": False}}}
            return httpx.Response(200, json=self.forms[fid])
        fid, _, action = p.lstrip("/").partition(":")
        fid, _, sub = fid.partition("/")
        sub2 = ""
        if "/" in sub:
            sub, _, sub2 = sub.partition("/")   # v0.213: responses/{response_id}
        if fid not in self.forms:
            return httpx.Response(404, json={"error": {"message": "not found"}})
        f = self.forms[fid]
        if action == "batchUpdate":
            self.batches.append(body["requests"])
            for r in body["requests"]:
                if "updateFormInfo" in r:
                    for k in r["updateFormInfo"]["updateMask"].split(","):
                        f["info"][k] = r["updateFormInfo"]["info"][k]
                elif "updateSettings" in r:
                    s = r["updateSettings"]["settings"]
                    if "quizSettings" in s:
                        f["settings"]["quizSettings"] = s["quizSettings"]
                    if "emailCollectionType" in s:
                        f["settings"]["emailCollectionType"] = s["emailCollectionType"]
                elif "createItem" in r:
                    it = json.loads(json.dumps(r["createItem"]["item"]))
                    it["itemId"] = self._id("i")[:8]
                    if "questionItem" in it:
                        if it["questionItem"]["question"].get("grading") and not f["settings"].get("quizSettings", {}).get("isQuiz"):
                            return httpx.Response(400, json={"error": {"message": "grading needs quiz"}})
                        it["questionItem"]["question"]["questionId"] = self._id("q")[:8]
                    if "questionGroupItem" in it and "question" in it["questionGroupItem"]:   # v0.213 grid
                        it["questionGroupItem"]["question"]["questionId"] = self._id("q")[:8]
                    f["items"].insert(r["createItem"]["location"]["index"], it)
                elif "updateItem" in r:
                    i = r["updateItem"]["location"]["index"]
                    f["items"][i] = {**f["items"][i], **r["updateItem"]["item"]}
                elif "deleteItem" in r:
                    del f["items"][r["deleteItem"]["location"]["index"]]
                elif "moveItem" in r:                                                      # v0.213 moveItem
                    i = r["moveItem"]["location"]["index"]
                    t = r["moveItem"]["toLocation"]["index"]
                    f["items"].insert(t, f["items"].pop(i))
            return httpx.Response(200, json={"form": f} if body.get("includeFormInResponse") else {})
        if action == "setPublishSettings":
            f["publishSettings"] = body["publishSettings"]
            return httpx.Response(200, json={"formId": fid})
        if sub == "responses":
            rs = self.responses.get(fid, [])
            if sub2:                                       # v0.213: forms.responses.get - one response by id
                self.single_response_gets.append((fid, sub2))
                one = [r for r in rs if r["responseId"] == sub2]
                return httpx.Response(200, json=one[0]) if one else httpx.Response(404, json={"error": {"message": "no response"}})
            flt = params.get("filter", "")
            if flt.startswith("timestamp > "):
                since = flt.removeprefix("timestamp > ")
                rs = [r for r in rs if r["lastSubmittedTime"] > since]
            return httpx.Response(200, json={"responses": rs} if rs else {})
        return httpx.Response(200, json=f)

    def answer(self, fid, by_title: dict, at: str, email: str = "", score=None):
        f = self.forms[fid]
        qid = {it["title"]: it["questionItem"]["question"]["questionId"] for it in f["items"] if "questionItem" in it}
        r = {"responseId": self._id("r"), "createTime": at, "lastSubmittedTime": at,
             "answers": {qid[t]: {"questionId": qid[t], "textAnswers": {"answers": [{"value": v} for v in
                                                                                  (val if isinstance(val, list) else [val])]}}
                         for t, val in by_title.items()}}
        if email:
            r["respondentEmail"] = email
        if score is not None:
            r["totalScore"] = score
        self.responses.setdefault(fid, []).append(r)


@pytest.fixture
def fake(env, monkeypatch):
    for k, v in {"SECRET_KEY": "test-secret-key-0123456789-abcdefghij", "PUBLIC_BASE_URL": "https://s.example.in",
                 "GOOGLE_OAUTH_CLIENT_ID": "cid", "GOOGLE_OAUTH_CLIENT_SECRET": "csec"}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.mailbox import accounts as ma
    f = FakeForms()
    ma.set_http(httpx.Client(transport=httpx.MockTransport(f)))
    yield f
    ma.set_http(None)


def _connect():
    from app.forms import accounts as fa
    url = fa.start_link("default")
    q = parse_qs(urlparse(url).query)
    assert "https://www.googleapis.com/auth/forms.body" in q["scope"][0] and q["state"][0].startswith("gfm_")
    assert fa.is_link_state(q["state"][0])
    v = fa.finish_link("code", q["state"][0])
    assert v["address"] == ME and v["tenant"] == "default"
    return v


def run(name, args, ctx):
    return asyncio.run(ft.FORMS_HANDLERS[name](ctx, **args))


EVENT_FORM = [
    {"title": "Aapka naam", "type": "short", "required": True},
    {"title": "Kaunsa din aayenge?", "type": "choice", "options": ["Shanivaar", "Ravivaar"], "required": True},
    {"title": "Kya laayenge?", "type": "checkbox", "options": ["Khana", "Music", "Games"], "allow_other": True},
    {"title": "Event kaisa laga?", "type": "scale", "low": 1, "high": 5, "low_label": "Bekaar", "high_label": "Badhiya"},
    {"title": "Sujhav", "type": "paragraph"},
]


def _executor():
    from app.bazar.connectors.forms import FormsExecutor
    from app.bazar.packs.registry import Pack
    pack = Pack(**json.loads((Path(__file__).parents[1] / "app/bazar/packs/manifests/santosh-forms.json").read_text()))
    return FormsExecutor(), pack, SimpleNamespace(user=SimpleNamespace(id="default"))


def test_not_connected_points_to_profile(env):
    with pytest.raises(ToolError, match="Profile > Google Forms"):
        run("form_find", {}, Ctx("someone", "c"))


def test_old_link_and_wrong_state_refused(fake):
    from app.forms import accounts as fa
    from app.forms.client import FormError
    with pytest.raises(FormError, match="purana"):
        fa.finish_link("code", "gfm_nope")


def test_create_publish_and_card(fake):
    from tests.test_bazar import _events
    _connect()
    ctx = conv_ctx()
    out = run("form_create", {"title": "Diwali Milan 2026", "description": "Sabko aamantran", "questions": EVENT_FORM,
                              "collect_emails": True}, ctx)
    assert out["created"] and out["responder_link"].endswith("/viewform") and "/edit" in out["edit_link"]
    assert len(out["questions"]) == 5 and out["questions"][0].endswith("(short, required)")
    f = fake.forms[out["id"]]
    assert f["info"]["description"] == "Sabko aamantran"
    assert f["publishSettings"]["publishState"] == {"isPublished": True, "isAcceptingResponses": True}
    cb = f["items"][2]["questionItem"]["question"]["choiceQuestion"]
    assert cb["type"] == "CHECKBOX" and cb["options"][-1] == {"isOther": True}
    assert f["items"][3]["questionItem"]["question"]["scaleQuestion"] == {"low": 1, "high": 5, "lowLabel": "Bekaar", "highLabel": "Badhiya"}
    assert f["settings"]["emailCollectionType"] == "RESPONDER_INPUT"
    card = _events(ctx.conversation_id, "form")[-1]
    assert card["title"] == "Diwali Milan 2026" and card["status"] == "created" and card["questions"] == 5


def test_bad_questions_are_refused_before_anything_is_made(fake):
    _connect()
    with pytest.raises(ToolError, match="options"):
        run("form_create", {"title": "X", "questions": [{"title": "Pick", "type": "choice"}]}, conv_ctx())
    with pytest.raises(ToolError, match="type"):
        run("form_create", {"title": "X", "questions": [{"title": "Q", "type": "video"}]}, conv_ctx())
    assert fake.forms == {}


def test_quiz_with_answers_and_scores(fake):
    _connect()
    ctx = conv_ctx()
    out = run("form_create", {"title": "GK Quiz", "questions": [
        {"title": "Bharat ki rajdhani?", "type": "choice", "options": ["Mumbai", "Delhi"], "correct": "Delhi", "points": 2},
        {"title": "2+2?", "type": "short", "correct": "4"}]}, ctx)
    assert out["is_quiz"]
    reqs = fake.batches[0]
    assert "updateSettings" in reqs[0]                         # quiz mode switched on before graded questions
    g = fake.forms[out["id"]]["items"][0]["questionItem"]["question"]["grading"]
    assert g == {"pointValue": 2, "correctAnswers": {"answers": [{"value": "Delhi"}]}}
    with pytest.raises(ToolError, match="options mein nahi"):
        run("form_create", {"title": "Bad", "questions": [{"title": "Q", "type": "choice", "options": ["a"], "correct": "b"}]}, ctx)
    fake.answer(out["id"], {"Bharat ki rajdhani?": "Delhi", "2+2?": "4"}, "2026-10-19T10:00:00Z", score=3)
    fake.answer(out["id"], {"Bharat ki rajdhani?": "Mumbai", "2+2?": "5"}, "2026-10-19T11:00:00Z", score=0)
    s = run("form_summary", {"form": "GK Quiz"}, ctx)
    assert s["quiz"] == {"average_score": 1.5, "best": 3, "lowest": 0}
    assert s["questions"][0]["counts"] == {"Delhi": 1, "Mumbai": 1}


def test_answers_table_summary_and_find_by_name(fake):
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Diwali Milan 2026", "questions": EVENT_FORM}, ctx)["id"]
    fake.answer(fid, {"Aapka naam": "Raju", "Kaunsa din aayenge?": "Shanivaar", "Kya laayenge?": ["Khana", "Music"],
                      "Event kaisa laga?": "5", "Sujhav": "Jaldi shuru karein"}, "2026-10-19T10:00:00Z", email="raju@x.in")
    fake.answer(fid, {"Aapka naam": "Sita", "Kaunsa din aayenge?": "Ravivaar", "Kya laayenge?": ["Khana"],
                      "Event kaisa laga?": "3"}, "2026-10-19T12:00:00Z", email="sita@x.in")
    found = run("form_find", {"query": "diwali"}, ctx)
    assert found["forms"][0]["id"] == fid
    r = run("form_responses", {"form": "Diwali Milan 2026"}, ctx)
    assert r["total"] == 2 and r["rows"][0]["Aapka naam"] == "Sita"           # newest first
    assert r["rows"][1]["Kya laayenge?"] == "Khana, Music" and r["rows"][1]["Email"] == "raju@x.in"
    s = run("form_summary", {"form": fid}, ctx)
    q = {x["question"]: x for x in s["questions"]}
    assert q["Kaunsa din aayenge?"]["counts"] == {"Shanivaar": 1, "Ravivaar": 1}
    assert q["Kya laayenge?"]["counts"]["Khana"] == 2 and q["Kya laayenge?"]["counts"]["Games"] == 0
    assert q["Event kaisa laga?"]["average"] == 4.0 and q["Event kaisa laga?"]["distribution"] == {"3": 1, "5": 1}
    assert q["Sujhav"]["latest"] == ["Jaldi shuru karein"] and s["responses"] == 2
    with pytest.raises(ToolError, match="EDIT link"):
        run("form_responses", {"form": "https://docs.google.com/forms/d/e/1FAIpQLSabc/viewform"}, ctx)


def test_two_forms_same_name_asks_which(fake):
    _connect()
    ctx = conv_ctx()
    run("form_create", {"title": "Feedback", "questions": [{"title": "Q"}]}, ctx)
    run("form_create", {"title": "Feedback", "questions": [{"title": "Q"}]}, ctx)
    from app.db import session
    from app.forms.models import FormsRecent
    with session() as s:
        s.query(FormsRecent).delete()
    with pytest.raises(ToolError, match="kai forms"):
        run("form_summary", {"form": "Feedback"}, ctx)


def test_edit_add_update_and_remove_unanswered_at_once(fake):
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Order form", "questions": [
        {"title": "Naam", "type": "short"}, {"title": "Item", "type": "dropdown", "options": ["Atta", "Tel"]},
        {"title": "Purana sawaal", "type": "short"}]}, ctx)["id"]
    out = run("form_edit", {"form": fid, "title": "Diwali order form",
                            "add": [{"title": "Delivery date", "type": "date", "required": True}],
                            "update": [{"question": "Item", "options": ["Atta", "Tel", "Chawal"], "required": True}],
                            "remove": ["3"]}, ctx)
    titles = [q.split(". ", 1)[1].split(" (")[0] for q in out["form"]["questions"]]
    assert titles == ["Naam", "Item", "Delivery date"] and "pending_id" not in out
    f = fake.forms[fid]
    assert f["info"]["title"] == "Diwali order form"
    item_q = f["items"][1]["questionItem"]["question"]
    assert [o["value"] for o in item_q["choiceQuestion"]["options"]] == ["Atta", "Tel", "Chawal"] and item_q["required"]


def test_removing_answered_question_needs_card(fake, monkeypatch):
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Survey", "questions": [{"title": "A"}, {"title": "B"}]}, ctx)["id"]
    fake.answer(fid, {"A": "x", "B": "y"}, "2026-10-19T10:00:00Z")
    ex, pack, bctx = _executor()
    seen = {}

    def card(c, pid):
        na = ex.call(pack, "confirm_change", {"pending_id": pid}, bctx)
        seen["na"] = na
        return {"needs_approval": True}
    monkeypatch.setattr(ft, "_card", card)
    out = run("form_edit", {"form": fid, "remove": ["B"]}, ctx)
    assert out["needs_approval"] and len(fake.forms[fid]["items"]) == 2      # not removed yet
    na = seen["na"]
    assert na.title == "Jawab wale sawaal hatayein?" and "B" in json.dumps(na.items)
    res = ex.execute(pack, na.action["name"], na.action["args"], bctx)
    assert "1 sawaal" in res["message"] and [i["title"] for i in fake.forms[fid]["items"]] == ["A"]
    from app.bazar.connectors.base import ToolError as BzErr
    with pytest.raises(BzErr):                                                # a card runs once
        ex.execute(pack, na.action["name"], na.action["args"], bctx)


def test_share_needs_card_and_names_resolve(fake, monkeypatch):
    _connect()
    from app.mailbox import contacts
    contacts.learn("default", [("Swati Sirsath", "swati@fnw.in")], 1.0, sent=True)
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Team form", "questions": [{"title": "Q"}]}, ctx)["id"]
    ex, pack, bctx = _executor()
    seen = {}
    monkeypatch.setattr(ft, "_card", lambda c, pid: seen.setdefault("na", ex.call(pack, "confirm_change", {"pending_id": pid}, bctx))
                        and {"needs_approval": True})
    out = run("form_share", {"form": fid, "people": ["Swati"]}, ctx)
    assert out["status"] == "needs_approval" and fake.shares == []
    ex.execute(pack, "run", seen["na"].action["args"], bctx)
    assert fake.shares[0][0] == fid and fake.shares[0][1] == {"type": "user", "role": "writer", "emailAddress": "swati@fnw.in"}
    with pytest.raises(ToolError, match="nahi mila"):
        run("form_share", {"form": fid, "people": ["Kishore"]}, ctx)


def test_open_close_and_quiz_toggle(fake):
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Reg", "questions": [{"title": "Naam"}]}, ctx)["id"]
    out = run("form_settings", {"form": fid, "accepting": False}, ctx)
    assert out["accepting"] is False
    assert fake.forms[fid]["publishSettings"]["publishState"]["isAcceptingResponses"] is False
    assert run("form_settings", {"form": fid, "quiz": True}, ctx)["is_quiz"] is True


def test_export_to_sheet_or_phone(fake, monkeypatch):
    from tests.test_bazar import _events
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Diwali Milan", "questions": EVENT_FORM}, ctx)["id"]
    fake.answer(fid, {"Aapka naam": "Raju", "Kaunsa din aayenge?": "Shanivaar"}, "2026-10-19T10:00:00Z")
    out = run("form_export", {"form": fid, "to": "phone"}, ctx)
    assert out["exported_to"] == "phone" and out["file"]["name"].endswith(".xlsx")
    card = _events(ctx.conversation_id, "pc_file")[-1]
    assert card["name"] == out["file"]["name"]
    import io

    import openpyxl
    from app.db import PcFile, session
    with session() as s:
        path = s.get(PcFile, out["file"]["file_id"]).stored_path
    ws = openpyxl.load_workbook(io.BytesIO(Path(path).read_bytes())).active
    rows = list(ws.values)
    assert rows[0][:2] == ("Submitted", "Aapka naam") and rows[1][1] == "Raju"
    made = {}
    import app.sheets.accounts as sa
    import app.sheets.service as ss
    monkeypatch.setattr(sa, "has_sheets", lambda t: True)
    monkeypatch.setattr(ss, "create", lambda tenant, title, tabs=None, account=None: made.update(title=title, tabs=tabs)
                        or {"id": "sh1", "title": title, "link": "https://docs.google.com/spreadsheets/d/sh1"})
    out = run("form_export", {"form": fid}, ctx)
    assert out["exported_to"] == "google_sheet" and made["title"] == "Diwali Milan - jawab"
    assert made["tabs"][0]["header"][1] == "Aapka naam" and made["tabs"][0]["rows"][0][1] == "Raju"
    assert _events(ctx.conversation_id, "sheet")[-1]["link"].endswith("/sh1")


def test_new_answer_alerts(fake):
    from tests.test_bazar import _notices
    from app.forms import service as fs
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Admission", "questions": [{"title": "Naam"}]}, ctx)["id"]
    fake.answer(fid, {"Naam": "Old"}, "2026-10-19T09:00:00Z")
    out = run("form_alerts", {"form": fid, "on": True}, ctx)
    assert out["alerts"] and out["responses_so_far"] == 1
    assert fs.alerts_tick() == 0                                               # nothing new yet
    fake.answer(fid, {"Naam": "Asha"}, "2026-10-19T10:00:00Z", email="asha@x.in")
    fake.answer(fid, {"Naam": "Ravi"}, "2026-10-19T10:05:00Z")
    assert fs.alerts_tick() == 1
    assert any("Form 'Admission' par 2 naye jawab" in (n or "") and "asha@x.in" in n for n in _notices(ctx.conversation_id))
    assert fs.alerts_tick() == 0                                               # told once
    assert run("form_alerts", {}, ctx)["watching"][0]["seen"] == 3
    run("form_alerts", {"form": fid, "on": False}, ctx)
    fake.answer(fid, {"Naam": "Late"}, "2026-10-19T11:00:00Z")
    assert fs.alerts_tick() == 0


def test_api_routes_and_finish_page(fake):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.forms import api
    from app.main import current_tenant, require_key
    app_ = FastAPI()
    app_.include_router(api.make_router(require_key, current_tenant))
    app_.add_api_route("/cb", api.finish_page)
    with TestClient(app_) as c:
        url = c.get("/api/forms/link").json()["url"]
        state = parse_qs(urlparse(url).query)["state"][0]
        page = c.get("/cb", params={"code": "c", "state": state})
        assert page.status_code == 200 and ME in page.text and "santosh://forms?ok=1" in page.text
        st = c.get("/api/forms/accounts").json()
        assert st["accounts"][0]["address"] == ME and st["can_link"]
        assert c.delete(f"/api/forms/accounts/{st['accounts'][0]['key']}").json()["accounts"] == []
        bad = c.get("/cb", params={"error": "access_denied"})
        assert bad.status_code == 400 and "ok=0" in bad.text


# ---- v0.213 Google Forms 100% coverage: move / page / grid / upload / media / delete / copy /
# settings published+emails / single response / quiz feedback ----

def test_move_reorders_questions(fake):
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Order", "questions": [
        {"title": "Naam", "type": "short"}, {"title": "Item", "type": "short"}, {"title": "Date", "type": "date"}]}, ctx)["id"]
    out = run("form_move", {"form": fid, "question": "Date", "new_index": 1}, ctx)
    titles = [q.split(". ", 1)[1].split(" (")[0] for q in out["questions"]]
    assert titles == ["Date", "Naam", "Item"] and out["moved"] == "Date" and out["to"] == 1
    with pytest.raises(ToolError, match="new_index"):
        run("form_move", {"form": fid, "question": "Naam", "new_index": 9}, ctx)


def test_page_grid_upload_item_types(fake):
    _connect()
    ctx = conv_ctx()
    out = run("form_create", {"title": "Club admission", "questions": [
        {"title": "Aapka naam", "type": "short"},
        {"title": "Khed details", "type": "page", "description": "Yahan se naya page shuru"},
        {"title": "Din aur samay", "type": "grid", "rows": ["Somvaar", "Mangalvaar"], "columns": ["Subah", "Sham"]},
        {"title": "Kya kya aa sakta hai", "type": "checkbox_grid", "rows": ["Khana", "Music"],
         "columns": ["Haan", "Nahi"]},
        {"title": "Resume", "type": "upload", "max_files": 2, "max_file_mb": 5, "file_types": ["PDF", "DOCX"]},
        {"title": "Kitna samay lagega?", "type": "time", "duration": True}]}, ctx)
    f = fake.forms[out["id"]]
    assert "pageBreakItem" in f["items"][1] and f["items"][1]["description"] == "Yahan se naya page shuru"
    g = f["items"][2]["questionGroupItem"]
    assert [r["value"] for r in g["grid"]["rows"]] == ["Somvaar", "Mangalvaar"]
    assert [c["value"] for c in g["grid"]["columns"]] == ["Subah", "Sham"]
    assert "type" not in g["grid"]                                    # mc grid: one answer per row
    assert f["items"][3]["questionGroupItem"]["grid"]["type"] == "CHECKBOX"   # checkbox grid: many
    fq = f["items"][4]["questionItem"]["question"]["fileUploadQuestion"]
    assert fq["maxFiles"] == 2 and fq["maxFileSizeMb"] == 5 and fq["types"] == ["PDF", "DOCX"]
    assert f["items"][5]["questionItem"]["question"]["timeQuestion"] == {"duration": True}
    kinds = [q.split(" (")[1].split(",")[0].rstrip(")") for q in out["questions"]]
    assert kinds == ["short", "page", "grid", "grid", "upload", "time"]
    with pytest.raises(ToolError, match="rows aur columns"):
        run("form_create", {"title": "Bad grid", "questions": [{"title": "G", "type": "grid", "rows": ["r"]}]}, ctx)


def test_quiz_feedback_fields(fake):
    _connect()
    ctx = conv_ctx()
    out = run("form_create", {"title": "Spoken English test", "questions": [
        {"title": "Plural of 'child'?", "type": "choice", "options": ["childs", "children"], "correct": "children",
         "points": 1, "feedback": "Children is the irregular plural.",
         "feedback_right": "Shabaash!", "feedback_wrong": "Revision chahiye."}]}, ctx)
    g = fake.forms[out["id"]]["items"][0]["questionItem"]["question"]["grading"]
    assert g["generalFeedback"] == {"text": "Children is the irregular plural."}
    assert g["whenRight"] == {"text": "Shabaash!"} and g["whenWrong"] == {"text": "Revision chahiye."}
    assert out["is_quiz"]


def test_media_image_and_video(fake):
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Photo contest", "questions": [{"title": "Naam"}]}, ctx)["id"]
    out = run("form_media", {"form": fid, "kind": "image", "uri": "https://example.in/poster.jpg",
                              "title": "Poster", "description": "Event ka poster"}, ctx)
    assert out["added"] == "image" and out["at"] == 2
    img = fake.forms[fid]["items"][1]["imageItem"]["image"]
    assert img["sourceUri"] == "https://example.in/poster.jpg" and img["altText"] == "Poster"
    out = run("form_media", {"form": fid, "kind": "video", "uri": "https://youtube.com/watch?v=abc", "index": 1}, ctx)
    assert out["added"] == "video" and out["at"] == 1
    assert fake.forms[fid]["items"][0]["videoItem"]["video"]["youtubeUri"] == "https://youtube.com/watch?v=abc"
    with pytest.raises(ToolError, match="kind"):
        run("form_media", {"form": fid, "kind": "audio", "uri": "x"}, ctx)
    with pytest.raises(ToolError, match="uri"):
        run("form_media", {"form": fid, "kind": "image", "uri": ""}, ctx)


def test_form_delete_card_flow(fake, monkeypatch):
    """form_delete queues a confirm card; the executor's approval moves the form to Drive Trash."""
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Old survey", "questions": [{"title": "Q"}]}, ctx)["id"]
    ex, pack, bctx = _executor()
    seen = {}
    monkeypatch.setattr(ft, "_card", lambda c, pid: seen.setdefault("na", ex.call(pack, "confirm_change", {"pending_id": pid}, bctx))
                        and {"needs_approval": True})
    out = run("form_delete", {"form": fid}, ctx)
    assert out["needs_approval"] and fake.trashed == []
    na = seen["na"]
    assert na.title == "Form delete karein?" and "Trash" in json.dumps(na.items)
    res = ex.execute(pack, na.action["name"], na.action["args"], bctx)
    assert "Trash" in res["message"] and fake.trashed == [fid]


def test_copy_duplicates_form(fake):
    from tests.test_bazar import _events
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "August feedback", "questions": EVENT_FORM}, ctx)["id"]
    out = run("form_copy", {"form": fid, "new_title": "September feedback"}, ctx)
    cp = out["copy"]
    assert cp["title"] == "September feedback" and cp["id"] != fid and len(cp["questions"]) == 5
    assert fake.copies == [(fid, "September feedback")]
    card = _events(ctx.conversation_id, "form")[-1]
    assert card["title"] == "September feedback" and card["status"] == "created"
    src, dst = fid, cp["id"]
    assert len(fake.forms[dst]["items"]) == len(fake.forms[src]["items"])


def test_settings_published_and_emails(fake):
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Reg", "questions": [{"title": "Naam"}]}, ctx)["id"]
    out = run("form_settings", {"form": fid, "published": False}, ctx)
    assert out["published"] is False and out["accepting"] is False
    assert fake.forms[fid]["publishSettings"]["publishState"]["isPublished"] is False
    back = run("form_settings", {"form": fid, "published": True}, ctx)
    assert back["published"] is True and back["accepting"] is True
    run("form_settings", {"form": fid, "emails": "verify"}, ctx)
    assert fake.forms[fid]["settings"]["emailCollectionType"] == "VERIFIED_EMAIL"
    run("form_settings", {"form": fid, "emails": "off"}, ctx)
    assert fake.forms[fid]["settings"]["emailCollectionType"] == "DONT_COLLECT"
    with pytest.raises(ToolError, match="off / collect / verify"):
        run("form_settings", {"form": fid, "emails": "maybe"}, ctx)


def test_single_response_get(fake):
    _connect()
    ctx = conv_ctx()
    fid = run("form_create", {"title": "Admission", "questions": [{"title": "Naam"}]}, ctx)["id"]
    fake.answer(fid, {"Naam": "Raju"}, "2026-10-19T10:00:00Z", email="raju@x.in")
    fake.answer(fid, {"Naam": "Sita"}, "2026-10-19T11:00:00Z", email="sita@x.in")
    rid = fake.responses[fid][0]["responseId"]
    one = run("form_responses", {"form": fid, "response_id": rid}, ctx)
    assert one["total"] == 1 and one["rows"][0]["Naam"] == "Raju" and one["response_id"] == rid
    assert fake.single_response_gets == [(fid, rid)]
    with pytest.raises(Exception):
        run("form_responses", {"form": fid, "response_id": "nope"}, ctx)
