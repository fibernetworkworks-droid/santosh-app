"""v0.581 STEP 7 CHECKPOINT, half 1: a coaching LMS from one line (docs/WEB_PLATFORM_PLAN.md Step 7 checkpoint).

Courses, video lessons, quizzes, certificates, subscriptions and live doubt chat - and every safety gate green on the
built site. What the engine needed and now has (general, not LMS-only):
- `gates`: a list read only through a pass list (lessons only with an Active membership; notes only for an enrolment
  in THAT course) - a new read rule `gated`, checked on the server per row, and a lesson's video follows its lesson.
- `subscription_list`: her AutoPay plan's state lands as a row (Active / Ended) from the gateway's signed events only,
  so a gate reads it like any other row; cancel = Ended = locked again.
- `documents`: a PDF from a row (a certificate) through the checked template, only for whoever may read the row, only
  when its `when` holds (a failed attempt gets no certificate).
- field types `video` (an MP4 upload, played in the page) and `url` (https only; a YouTube lesson)."""
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_v0419_paisa import FakeRazorpay, SECRET  # noqa: F401
from tests.test_v0446_dukaan_paisa import _hook
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.757.0"


LMS_SPEC = {
    "name": "Disha Coaching", "summary": "Online coaching: courses, video lessons, quizzes, certificates, monthly membership, doubt chat.",
    "field_hint": "coaching", "goal": "enquiry",
    "roles": [{"key": "student", "label": "Student", "can": "membership le, lessons dekhe, quiz de, certificate le, doubt pooche"},
              {"key": "teacher", "label": "Teacher", "can": "lessons aur quiz banaye, doubts ka jawab de"}],
    "stories": [{"who": "Student", "want": "membership lekar video lessons dekhna", "so": "ghar se padh sakun"},
                {"who": "Student", "want": "quiz pass karke certificate lena", "so": ""},
                {"who": "Teacher", "want": "doubt ka jawab dena", "so": ""}],
    "pages": [{"title": "Home", "purpose": "coaching", "for": "public"}, {"title": "Courses", "purpose": "list", "for": "public"},
              {"title": "Fees", "purpose": "membership", "for": "public"}, {"title": "Contact", "purpose": "pata", "for": "public"},
              {"title": "My learning", "purpose": "lessons, quiz, certificate", "for": "member"}],
    "payments": {"mode": "online", "what": "monthly membership (AutoPay)"},
    "notifications": [{"when": "certificate ready", "who": "row_owner", "how": "in_app"}],
    "integrations": [],
    "features": {"shop": False, "blog": False, "booking": False, "languages": []},
    "app_words": "courses; lessons with a video or a YouTube link, only for members with an active membership; "
                 "enrolments; notes per course only for those enrolled; quizzes; attempts scored by the server; certificate",
    "page_count": 4, "questions": []}

STAFF = {"rules": {"create": "admin", "read": "members", "update": "admin", "delete": "admin"}}
LMS_LOGIC = {
    "summary": "Membership se lesson, quiz se certificate", "questions": [], "fields": [],
    "lists": [
        {"key": "courses", "label": "Courses", **STAFF,
         "fields": [{"key": "title", "label": "Course", "type": "text", "required": True}]},
        {"key": "lessons", "label": "Lessons", **STAFF,
         "fields": [{"key": "title", "label": "Lesson", "type": "text", "required": True},
                    {"key": "course", "label": "Course", "type": "ref", "to": "courses", "required": True},
                    {"key": "video", "label": "Video", "type": "video"},
                    {"key": "youtube", "label": "YouTube link", "type": "url"}]},
        {"key": "memberships", "label": "Memberships",
         "rules": {"create": "admin", "read": "own", "update": "admin", "delete": "admin"},
         "fields": [{"key": "plan", "label": "Plan", "type": "text"},
                    {"key": "status", "label": "Status", "type": "choice", "options": ["Active", "Ended"]}]},
        {"key": "enrolments", "label": "Enrolments",
         "rules": {"create": "admin", "read": "own", "update": "admin", "delete": "admin"},
         "fields": [{"key": "course", "label": "Course", "type": "ref", "to": "courses", "required": True},
                    {"key": "status", "label": "Status", "type": "choice", "options": ["Active", "Dropped"]}]},
        {"key": "notes", "label": "Notes", **STAFF,
         "fields": [{"key": "course", "label": "Course", "type": "ref", "to": "courses", "required": True},
                    {"key": "text", "label": "Note", "type": "long_text"}]},
        {"key": "quizzes", "label": "Quizzes", **STAFF,
         "fields": [{"key": "course", "label": "Course", "type": "ref", "to": "courses"},
                    {"key": "q1", "label": "Q1", "type": "text"}, {"key": "q2", "label": "Q2", "type": "text"},
                    {"key": "a1", "label": "Answer 1", "type": "text", "private": True},
                    {"key": "a2", "label": "Answer 2", "type": "text", "private": True},
                    {"key": "pass_mark", "label": "Pass mark", "type": "number"}]},
        {"key": "attempts", "label": "Attempts",
         "rules": {"create": "member", "read": "own", "update": "admin", "delete": "admin"},
         "fields": [{"key": "quiz", "label": "Quiz", "type": "ref", "to": "quizzes", "required": True},
                    {"key": "student_name", "label": "Name", "type": "text", "required": True},
                    {"key": "r1", "label": "Reply 1", "type": "text"}, {"key": "r2", "label": "Reply 2", "type": "text"},
                    {"key": "score", "label": "Score", "type": "number"}]}],
    "logic": {
        "relations": [{"name": "course_lessons", "from": "lessons", "field": "course", "to": "courses", "label": "Lessons",
                       "on_delete": "restrict"}],
        "formulas": [{"coll": "attempts", "field": "score",
                      "expr": "if(lower(r1) == lower(quiz.a1), 1, 0) + if(lower(r2) == lower(quiz.a2), 1, 0)"}],
        "gates": [{"coll": "lessons", "pass": "memberships", "match": {"status": "Active"}},
                  {"coll": "notes", "pass": "enrolments", "via": "course", "pass_field": "course", "match": {"status": "Active"}}],
        "subscription_list": "memberships",
        "documents": [{"coll": "attempts", "title": "Certificate", "signer": "Disha Coaching",
                       "lines": ["This certifies that {{student_name}}", "passed the quiz with score {{score}}."],
                       "when": "score >= quiz.pass_mark"}],
        "labels": {"courses": "title", "quizzes": "q1"}}}


@pytest.fixture
def lms(site_env, monkeypatch):
    from app.appmaker import ai as AAI
    from app.paygate import gw as GW
    from app.site import ai as AI
    from app.site import architect as AR
    import httpx

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(AR.ARCH_SYSTEM[:40]):
            return json.loads(json.dumps(LMS_SPEC))
        return site_env(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    monkeypatch.setattr(AAI, "ask_json", lambda system, prompt, max_tokens=7000: json.loads(json.dumps(LMS_LOGIC)))
    f = FakeRazorpay()
    GW.set_transport(httpx.MockTransport(f))
    from app.main import app
    c = TestClient(app)
    card = c.post("/api/site-architect", json={"words": "coaching LMS - courses, video lessons, quiz, certificate, membership"}).json()
    got = c.post(f"/api/site-architect/{card['id']}/approve", json={"hash": card["hash"]}).json()
    sid = got["site"]
    base = f"/api/site-app/{sid}"
    for e, n in (("teacher@x.in", "Teacher"), ("riya@x.in", "Riya"), ("aman@x.in", "Aman")):
        assert c.post(f"{base}/signup", json={"email": e, "password": "pass-word-1", "name": n, "consent": True}).status_code == 200
    mem = {m["email"]: m["id"] for m in c.get(f"/api/sites/{sid}/app/members").json()["members"]}
    c.post(f"/api/sites/{sid}/app/members/{mem['teacher@x.in']}/role", json={"role": "admin"})
    h = {e: {"Authorization": "Bearer " + c.post(f"{base}/login", json={"email": e, "password": "pass-word-1"}).json()["token"]}
         for e in ("teacher@x.in", "riya@x.in", "aman@x.in")}
    yield c, sid, base, h, mem, f
    GW.set_transport(None)


def _mp4() -> bytes:
    return b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00" * 64


def _course(c, base, ht):
    course = c.post(f"{base}/c/courses", headers=ht, json={"title": "Class 10 Maths"}).json()
    vid = c.post(f"{base}/upload", headers=ht, content=_mp4()).json()
    assert vid.get("kind") == "video", vid
    lesson = c.post(f"{base}/c/lessons", headers=ht, json={"title": "Trigonometry 1", "course": course["id"], "video": vid["id"],
                                                           "youtube": "https://www.youtube.com/watch?v=abc123XYZ"}).json()
    assert lesson.get("id"), lesson
    return course, lesson, vid


def test_the_spec_carries_gates_subscription_and_documents(lms):
    from app.site import applink as AL
    from app.site import service as S
    from app.appmaker.logic import engine as LE
    c, sid, base, h, mem, f = lms
    p = AL.project(S._load(sid))
    sp = LE.spec_of(p)
    assert [g["coll"] for g in sp["gates"]] == ["lessons", "notes"] and sp["subscription_list"] == "memberships"
    assert sp["documents"][0]["coll"] == "attempts"
    sch = c.get(f"{base}/schema").json()
    lessons = next(x for x in sch["collections"] if x["key"] == "lessons")
    assert lessons["rules"]["read"] == "gated"


def test_spec_checker_refuses_bad_gates_and_documents():
    from app.appmaker.logic import spec as SP
    lists = LMS_LOGIC["lists"]
    sch = {"collections": [{"key": x["key"], "label": x["label"], "rules": x["rules"],
                            "fields": [{**fd} for fd in x["fields"]]} for x in lists]}
    bad = {"gates": [{"coll": "lessons", "pass": "lessons", "match": {"status": "Active"}},          # its own pass
                     {"coll": "notes", "pass": "enrolments", "via": "nope", "pass_field": "course", "match": {"status": "Active"}},
                     {"coll": "courses", "pass": "memberships", "match": {}},                         # no match
                     {"coll": "quizzes", "pass": "nolist", "match": {"status": "Active"}}],
           "subscription_list": "courses",                                                             # no plan / status
           "documents": [{"coll": "attempts", "lines": []},
                         {"coll": "courses", "lines": ["{{nope_field}} done"]}]}
    out = SP.check(bad, sch)
    errs = json.dumps(out.get("errors") if isinstance(out, dict) else out, ensure_ascii=False)
    assert "apna hi pass" in errs and "via" in errs and "match" in errs and "plan" in errs and "lines chahiye" in errs


def test_lessons_only_with_an_active_membership_and_the_video_follows(lms):
    c, sid, base, h, mem, f = lms
    ht, hr, ha = h["teacher@x.in"], h["riya@x.in"], h["aman@x.in"]
    course, lesson, vid = _course(c, base, ht)
    # nobody has a membership yet: the lesson list is empty for students, the video is not theirs to fetch
    assert c.get(f"{base}/c/lessons", headers=hr).json()["rows"] == []
    assert c.get(f"{base}/c/lessons").status_code in (401, 403)
    assert c.get(f"{base}/file/{vid['id']}", headers=hr).status_code == 404
    # a student cannot make her own membership row
    assert c.post(f"{base}/c/memberships", headers=hr, json={"plan": "Monthly", "status": "Active"}).status_code == 403
    # her AutoPay plan + gateway keys (her taps), Riya subscribes, the SIGNED webhook activates it
    con = c.post(f"/api/sites/{sid}/payments/connect").json()
    app_id = con["app"]
    assert c.put(f"/api/apps/{app_id}/pay/keys", json={"gateway": "razorpay", "keys": {
        "key_id": "rzp_test_abc", "key_secret": "sekret", "webhook_secret": SECRET}}).json()["on"]
    assert c.post(f"/api/apps/{app_id}/pay/plans", json={"name": "Monthly", "amount": "499", "period": "month", "count": 12,
                                                         "her_tap": True}).status_code == 200
    from app.site import applink as AL
    from app.site import service as S
    key = json.loads(AL.project(S._load(sid)).android)["app_key"]
    plan = c.get(f"{base}/pay/plans").json()["plans"][0]
    c.post(f"{base}/pay/plans/{plan['key']}/subscribe", headers=hr)
    # a forged (unsigned) event changes nothing
    import json as _j
    raw = _j.dumps({"event": "subscription.activated", "payload": {"subscription": {"entity": {"id": "sub_1"}}}}).encode()
    c.post(f"/api/app-api/{key}/pay/webhook", content=raw, headers={"X-Razorpay-Signature": "bad", "Content-Type": "application/json"})
    assert c.get(f"{base}/c/lessons", headers=hr).json()["rows"] == []
    _hook(c, key, {"event": "subscription.activated", "payload": {"subscription": {"entity": {"id": "sub_1", "status": "active"}}}})
    mine = c.get(f"{base}/c/memberships", headers=hr).json()["rows"]
    assert [(m["plan"], m["status"]) for m in mine] == [("Monthly", "Active")]
    rows = c.get(f"{base}/c/lessons", headers=hr).json()["rows"]
    assert [x["title"] for x in rows] == ["Trigonometry 1"] and rows[0]["youtube"].startswith("https://www.youtube.com/")
    got = c.get(f"{base}/file/{vid['id']}", headers=hr)
    assert got.status_code == 200 and got.headers["content-type"].startswith("video/mp4")
    # Aman never paid: still nothing
    assert c.get(f"{base}/c/lessons", headers=ha).json()["rows"] == []
    assert c.get(f"{base}/file/{vid['id']}", headers=ha).status_code == 404
    # a charge keeps it Active (no second row); a cancel ends it and the course locks again
    _hook(c, key, {"event": "subscription.charged", "payload": {"subscription": {"entity": {"id": "sub_1"}},
                                                                 "payment": {"entity": {"id": "pay_s1", "amount": 49900}}}})
    assert len(c.get(f"{base}/c/memberships", headers=hr).json()["rows"]) == 1
    sub = c.get(f"{base}/pay/subs", headers=hr).json()["subs"][0]
    assert c.post(f"{base}/pay/subs/{sub['id']}/cancel", headers=hr).json()["status"] == "cancelled"
    assert [m["status"] for m in c.get(f"{base}/c/memberships", headers=hr).json()["rows"]] == ["Ended"]
    assert c.get(f"{base}/c/lessons", headers=hr).json()["rows"] == []
    assert c.get(f"{base}/file/{vid['id']}", headers=hr).status_code == 404
    # the teacher (staff) always sees her own lessons
    assert len(c.get(f"{base}/c/lessons", headers=ht).json()["rows"]) == 1


def test_notes_only_for_those_enrolled_in_that_course(lms):
    c, sid, base, h, mem, f = lms
    ht, hr = h["teacher@x.in"], h["riya@x.in"]
    m10 = c.post(f"{base}/c/courses", headers=ht, json={"title": "Maths"}).json()
    sc = c.post(f"{base}/c/courses", headers=ht, json={"title": "Science"}).json()
    c.post(f"{base}/c/notes", headers=ht, json={"course": m10["id"], "text": "Maths formula sheet"})
    c.post(f"{base}/c/notes", headers=ht, json={"course": sc["id"], "text": "Science diagrams"})
    assert c.get(f"{base}/c/notes", headers=hr).json()["rows"] == []
    from app.site import applink as AL
    from app.site import service as S
    from app.appmaker.logic import engine as LE
    p = AL.project(S._load(sid))
    LE.system_create(p, "enrolments", {"course": m10["id"], "status": "Active"}, mem["riya@x.in"], "test enrol")
    assert [x["text"] for x in c.get(f"{base}/c/notes", headers=hr).json()["rows"]] == ["Maths formula sheet"]
    assert c.get(f"{base}/c/notes", headers=h["aman@x.in"]).json()["rows"] == []


def test_quiz_scored_by_the_server_and_certificate_only_when_passed(lms):
    c, sid, base, h, mem, f = lms
    ht, hr, ha = h["teacher@x.in"], h["riya@x.in"], h["aman@x.in"]
    qz = c.post(f"{base}/c/quizzes", headers=ht, json={"q1": "sin 90?", "q2": "cos 0?", "a1": "1", "a2": "1", "pass_mark": 2}).json()
    seen = c.get(f"{base}/c/quizzes", headers=hr).json()["rows"][0]
    assert "a1" not in seen and "a2" not in seen and seen["q1"] == "sin 90?"                       # answers never reach students
    good = c.post(f"{base}/c/attempts", headers=hr, json={"quiz": qz["id"], "student_name": "Riya", "r1": "1", "r2": "1", "score": 99}).json()
    assert good["score"] == 2                                                                          # the server scores it
    bad = c.post(f"{base}/c/attempts", headers=ha, json={"quiz": qz["id"], "student_name": "Aman", "r1": "0", "r2": "1"}).json()
    assert bad["score"] == 1
    pdf = c.get(f"{base}/c/attempts/{good['id']}/document", headers=hr)
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-" and pdf.headers["content-type"] == "application/pdf"
    assert c.get(f"{base}/c/attempts/{bad['id']}/document", headers=ha).status_code == 409           # not passed
    assert c.get(f"{base}/c/attempts/{good['id']}/document", headers=ha).status_code == 404          # not hers
    assert c.get(f"{base}/c/attempts/{good['id']}/document").status_code in (401, 404)
    from pypdf import PdfReader
    import io
    text = "".join(pg.extract_text() for pg in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Riya" in text and "score 2" in text and "Certificate" in text


def test_url_fields_take_https_only(lms):
    c, sid, base, h, mem, f = lms
    ht = h["teacher@x.in"]
    course = c.post(f"{base}/c/courses", headers=ht, json={"title": "Maths"}).json()
    r = c.post(f"{base}/c/lessons", headers=ht, json={"title": "x", "course": course["id"], "youtube": "javascript:alert(1)"})
    assert r.status_code == 400 and "https" in r.text


def test_live_doubt_chat_student_asks_teacher_answers(lms):
    c, sid, base, h, mem, f = lms
    hr, ha = h["riya@x.in"], h["aman@x.in"]
    assert c.post(f"{base}/chat", headers=hr, json={"text": "Sir, sin 30 kitna hota hai?"}).status_code == 200
    thread = c.get(f"{base}/chat", headers=hr).json()
    assert "sin 30" in json.dumps(thread, ensure_ascii=False)
    assert "sin 30" not in json.dumps(c.get(f"{base}/chat", headers=ha).json(), ensure_ascii=False)   # her doubt is hers


def test_the_built_lms_site_passes_every_gate(lms):
    from app.site import gates as G
    from app.site import service as S
    c, sid, base, h, mem, f = lms
    S.choose_look(T, sid, 0)
    r = S._load(sid)
    out = S._assemble_live(r)
    res = G.scan(out, S._ctx(r), {"source": "hoola+axe", "blocking": []}, S.form_endpoint(r))
    fails = [x for x in res["rows"] if x["state"] == "fail"]
    assert not fails, fails
    assert res["ok"]
    js = (out / "assets" / "hoola-app.js").read_text() if (out / "assets" / "hoola-app.js").exists() else ""
    if js:
        assert "youtube-nocookie.com/embed/" in js and "/document" in js


def test_the_author_is_taught_the_new_parts():
    from app.appmaker.logic import service as LS
    for w in ("gates", "subscription_list", "documents", "video", "url"):
        assert w in LS.AUTHOR_SYSTEM
