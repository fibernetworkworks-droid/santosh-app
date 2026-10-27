"""Film Desk (AI film producer on Hoola Video Studio): script -> breakdown -> shots by code / model, consent register gating
every real face / voice before the studio sees it (proof kept without EXIF, withdrawal, minors, famous people refused), storyboard
pushed into the REAL studio engine, budget = studio estimate, paid shots only as the studio's own price card, her caps, rights
register, release checklist per target (CBFC / OTT rating / disclosure), cards decided only by her tap with the hash, DPDP
forget, worker alerts, tools + API."""
import asyncio
import io
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.filmdesk.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)        # 10:30 am IST

SCRIPT = """INT. CHAI STALL - NIGHT
Rain falls. Meena wipes the counter.

MEENA
Aaj bhi koi nahi aaya.

RAJU: Main aaya na, didi!

EXT. STREET - DAY
Raju runs with a kite through the lane.
"""


@pytest.fixture
def fd(env, monkeypatch):
    from app.filmdesk import service as S
    from app.studio import service as SS
    SS._studios.clear()
    events, stored = [], []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(SS, "_publish", lambda *a, **k: None)
    monkeypatch.setattr(SS, "_note", lambda *a, **k: None)

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    monkeypatch.setattr(S, "_ask_json", lambda system, prompt, max_tokens=6000: {})
    clk = {"t": NOW}
    monkeypatch.setattr(S, "clock", lambda: clk["t"])
    S.EVENTS, S.STORED, S.CLK = events, stored, clk
    return S


def _photo(exif=True) -> bytes:
    from PIL import Image
    im = Image.new("RGB", (64, 48), (200, 120, 40))
    bio = io.BytesIO()
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "SecretCam"                  # Make
        ex[0x8825] = {2: (19.0, 4.0, 0.0)}        # GPS IFD (latitude)
        im.save(bio, "JPEG", exif=ex.tobytes())
    else:
        im.save(bio, "JPEG")
    return bio.getvalue()


def _file(name="form.jpg", data=None) -> str:
    from app.mailbox.service import store_bytes
    return store_bytes(T, name, data if data is not None else _photo()).id


def _film(S, **kw):
    p = S.project_new(T, title="Baarish Wali Chai", logline="Ek chai wali aur ek bachcha baarish mein dost bante hain",
                      fmt="short", language="Hindi", targets=kw.get("targets", ["youtube"]), budget_inr=kw.get("budget"))
    S.script_set(T, p["project"]["number"], SCRIPT)
    return p["project"]["number"]


def test_rules():
    from app.filmdesk import rules as R
    sc = R.parse_script(SCRIPT)
    assert [s["place"] for s in sc] == ["CHAI STALL", "STREET"] and sc[0]["time"] == "night" and sc[1]["time"] == "day"
    assert sc[0]["dialogue"] == [{"who": "Meena", "line": "Aaj bhi koi nahi aaya."}, {"who": "Raju", "line": "Main aaya na, didi!"}]
    hi = R.parse_script("Drishya 1 - Ghar - subah\nMaa: Uth ja beta\nBeta sota hai.\nदृश्य 2 स्कूल\nTeacher: Late kyun?")
    assert len(hi) == 2 and hi[0]["characters"] == ["Maa"] and hi[1]["characters"] == ["Teacher"]
    b = R.breakdown_summary(sc)
    assert b["scenes"] == 2 and b["night"] == 1 and {c["name"] for c in b["characters"]} == {"Meena", "Raju"}
    shots = R.shots_from_scene(sc[0])
    assert shots[0]["camera"] == "wide" and shots[1]["dialogue"] == "Aaj bhi koi nahi aaya." and all(4 <= s["duration"] <= 10 for s in shots)
    day = "2026-10-23"
    p = {"name": "Ritu", "real": True, "consent": {"status": "recorded", "uses": ["ai_likeness"], "until": "2026-12-31"}}
    assert R.consent_problem(p, "ai_likeness", day) == "" and "awaaz" in R.consent_problem(p, "ai_voice", day)
    assert "khatam" in R.consent_problem(p, "ai_likeness", "2027-01-05")
    assert "darj nahi" in R.consent_problem({"name": "X", "real": True, "consent": {}}, "ai_likeness", day)
    assert "wapas" in R.consent_problem({"name": "X", "real": True, "consent": {"status": "withdrawn"}}, "ai_likeness", day)
    assert "guardian" in R.consent_problem({"name": "B", "real": True, "minor": True, "consent": {"status": "recorded",
                                                                                                    "uses": ["ai_likeness"]}}, "ai_likeness", day)
    assert "personality" in R.consent_problem({"name": "Star", "real": True, "public_figure": True}, "ai_likeness", day)
    assert R.consent_problem({"name": "AI", "real": False}, "ai_voice", day) == ""
    song = {"title": "Dil", "kind": "song", "licence": "licensed", "proof": "abc", "platforms": ["youtube"], "sync": False}
    assert "sync" in R.rights_problem(song, ["youtube"], day)
    assert "OTT" in R.rights_problem({**song, "sync": True}, ["youtube", "ott"], day)
    assert R.rights_problem({**song, "sync": True}, ["youtube"], day) == ""
    assert "saboot" in R.rights_problem({**song, "proof": ""}, ["youtube"], day)
    assert R.rights_problem({"title": "Bed", "licence": "ai_generated"}, ["youtube"], day) == ""
    assert R.rating("UA 13+") == "UA13" and R.rating("U/A") == "UA13" and R.rating("x") == ""
    keys = {i["key"] for i in R.checklist(["theatrical", "youtube", "ott"], "feature", True)}
    assert {"cbfc", "access", "yt_altered", "ott_rating", "disclosure", "consents", "rights"} <= keys
    assert "AI" in R.disclosure("Marathi", ["youtube"])["description_line"] and R.disclosure("Hindi", ["youtube"])["steps"]
    assert R.clean("otp 123456 card 4111 1111 1111 1111") == "otp [hataya] card [hataya]"
    assert R.story_problem("an actor struggles in Mumbai") == "" and R.story_problem("Virat Kohli ka deepfake")
    assert R.targets_of("yt, insta, cinema") == ["youtube", "instagram", "theatrical"] and R.fmt("movie") == "feature"


def test_project_script_breakdown_shots(fd, monkeypatch):
    S = fd
    with pytest.raises(S.FilmError):
        S.project_new(T, title="Shah Rukh ka deepfake")                       # named famous person
    p = S.project_new(T, title="Baarish", logline="Chai wali aur bachcha. Baarish mein dosti.", targets="yt,insta")
    num = p["project"]["number"]
    assert num == "F-0001" and p["project"]["targets"] == ["youtube", "instagram"]
    r = S.script_write(T, num, "")                                             # no model -> honest frame from her words
    assert "[jagah]" in S.project_view(T, num)["script"] and "dhaancha" in r["say"]
    monkeypatch.setattr(S, "_ask_json", lambda system, prompt, max_tokens=6000:
                        {"script": SCRIPT, "notes": ["Raju ki umar nahi batayi"]} if "screenwriter" in system else {})
    r = S.script_write(T, num, "Meena 40 saal ki hai")
    assert r["breakdown"]["scenes"] == 2 and set(r["cast"]) == {"Meena", "Raju"} and r["notes"]
    v = S.project_view(T, num)
    assert v["script_versions"] and v["status"] == "breakdown"
    sh = S.shots_make(T, num)                                                  # model gives nothing -> code shots
    assert sh["made"] >= 3 and all(x["camera"] for x in sh["shots"][:1])
    ids = [x["id"] for x in sh["shots"]]
    S.shot_update(T, num, ids[0], prompt="Wide shot of a tin-roof chai stall in heavy rain at night", duration=7)
    with pytest.raises(S.FilmError):
        S.shot_update(T, num, ids[0], prompt="Deepika in the rain")             # famous person in a shot
    S.shot_update(T, num, ids[-1], delete=True)
    assert len(S.project_view(T, num)["shots"]) == len(ids) - 1
    monkeypatch.setattr(S, "_ask_json", lambda system, prompt, max_tokens=6000: {"shots": [
        {"prompt": "Meena pours chai, steam rising", "camera": "close_up", "duration": 30, "characters": ["Meena", "Stranger"],
         "dialogue": "Aaj bhi koi nahi aaya.", "speaker": "Meena"},
        {"prompt": "Salman dances", "camera": "orbit"}]})
    r = S.shots_make(T, num, scene="sc1")
    first = [x for x in r["shots"] if x["scene"] == "sc1"][0]
    assert first["duration"] == 10 and first["characters"] == ["Meena"] and r["dropped"]   # clamp, unknown char, famous dropped
    S.script_restore(T, num, 1)
    assert "[jagah]" in S.project_view(T, num)["script"]


def test_consent_gate_before_studio(fd):
    S = fd
    num = _film(S)
    S.shots_make(T, num, use_model=False)
    x = S.person_add(T, "Ritu Sharma", "actor", "98220 12345", photo_files=[_file("ritu.jpg")])["person"]
    assert x["number"] == "P-001" and x["phone_masked"].endswith("2345") and "phone" not in x
    S.cast_set(T, num, "Meena", person="P-001")
    with pytest.raises(S.FilmError) as e:
        asyncio.run(S.storyboard_push(T, num))
    assert "ijazat" in str(e.value)
    with pytest.raises(S.FilmError):
        S.consent_record(T, "P-001", "signed_form", _file(), ["ai_likeness"], actor="staff:s1")   # staff can't record
    with pytest.raises(S.FilmError):
        S.consent_record(T, "P-001", "signed_form", "", ["ai_likeness"])                        # no proof
    S.consent_record(T, "P-001", "signed_form", _file(), ["ai_likeness"], until="31-12-2026")
    with pytest.raises(S.FilmError) as e:
        asyncio.run(S.storyboard_push(T, num))                                    # she speaks: voice not in the consent
    assert "awaaz" in str(e.value)
    r = S.consent_record(T, "P-001", "video", _file("haan.jpg"), ["ai_likeness", "ai_voice", "promo"], until="2026-12-31")
    assert "ijazat darj" in r["say"]
    pv = S.person_view(T, "P-001")
    assert pv["consent"]["has_proof"] and len(pv["history"]) == 2
    from PIL import Image
    kept = [p for p in (S._home(T) / "consent" / "P-001").iterdir()]
    assert kept and all(not Image.open(p).getexif() for p in kept)               # EXIF / GPS / camera dropped
    out = asyncio.run(S.storyboard_push(T, num))
    assert out["characters_added"] == ["Meena"] and out["estimate"]["usd"] > 0
    from app.studio import service as SS
    sp = SS.studio_sync(T).load(out["studio_project"])
    assert "Meena" in sp["characters"] and sp["characters"]["Meena"]["consent"] and len(sp["shots"]) == out["shots"]
    # famous people and minors
    star = S.person_add(T, "Virat Kohli", "actor")["person"]
    assert star["public_figure"]
    with pytest.raises(S.FilmError):
        S.consent_record(T, star["number"], "signed_form", _file(), ["ai_likeness"])
    kid = S.person_add(T, "Chhotu", "actor", minor=True)["person"]
    with pytest.raises(S.FilmError):
        S.consent_record(T, kid["number"], "video", _file(), ["ai_likeness"])
    S.consent_record(T, kid["number"], "video", _file(), ["ai_likeness"], guardian="Sunita (maa)")
    # withdrawal stops every new paid shot
    w = S.consent_withdraw(T, "P-001", "Unhone mana kiya")
    assert num in w["projects"]
    with pytest.raises(S.FilmError) as e:
        asyncio.run(S.spend(T, num, "draft"))
    assert "wapas" in str(e.value)


def test_budget_and_paid_shots_only_on_studio_card(fd, monkeypatch):
    S = fd
    num = _film(S, budget=50)
    S.shots_make(T, num, use_model=False)
    with pytest.raises(S.FilmError):
        S.budget(T, num)                                                         # not in the studio yet
    asyncio.run(S.storyboard_push(T, num))
    b = S.budget(T, num)
    assert b["total"]["final"]["inr"] > b["total"]["draft"]["inr"] > 0 and b["spent_inr"] == 0 and b["shots"][0]["draft"]["inr"] > 0
    with pytest.raises(S.FilmError) as e:
        asyncio.run(S.spend(T, num, "final"))                                   # above her film budget
    assert "budget" in str(e.value)
    S.project_update(T, num, budget_inr=5000)
    with pytest.raises(S.FilmError):
        S.project_update(T, num, actor="staff:s1", budget_inr=99999)             # only she sets budgets
    calls = []
    from app.studio import service as SS
    real_generate = SS.generate
    monkeypatch.setattr(SS, "generate", lambda *a, **k: _fake_gen(calls, *a, **k))
    pv = asyncio.run(S.preview(T, num))
    assert calls[-1][2] == "preview" and pv["studio"]["started"]
    monkeypatch.setattr(SS, "generate", real_generate)                          # the real studio generate for paid shots
    r = asyncio.run(S.spend(T, num, "draft", actor="staff:s1"))                 # staff may ASK; the studio card waits for her
    aid = r["studio"]["waiting_owner"]
    sp = SS.studio_sync(T).load(S.project_view(T, num)["studio_project"])
    assert sp["approvals"][aid]["status"] == "pending" and sp["spent_usd"] == 0 and not sp["jobs"]
    assert "Studio ka card" in r["say"]
    S.shot_update(T, num, S.project_view(T, num)["shots"][0]["id"], duration=9)
    with pytest.raises(S.FilmError) as e:
        asyncio.run(S.spend(T, num, "draft"))                                   # shot list changed after the storyboard
    assert "dobara" in str(e.value)
    with pytest.raises(S.FilmError):
        asyncio.run(S.spend(T, num, "preview"))


async def _fake_gen(calls, tenant, project, quality="preview", *a, **k):
    calls.append((tenant, project, quality))
    return {"started": 3, "say": "Free preview ban raha hai."}


def test_release_checklist_cards_and_her_tap(fd, monkeypatch):
    S = fd
    num = _film(S, targets=["youtube", "theatrical"])
    S.shots_make(T, num, use_model=False)
    asyncio.run(S.storyboard_push(T, num))
    r = S.right_add(T, num, "song", "Baarish ka gaana", "Raag Music", "licensed", sync=False, platforms=["youtube"])
    assert "Dhyaan" in r["say"]
    rv = S.release_view(T, num)
    assert {"rights", "final_video", "cbfc", "credits", "yt_altered"} <= set(rv["blockers"]) and rv["cbfc_note"]
    with pytest.raises(S.FilmError):
        S.release_request(T, num)
    with pytest.raises(S.FilmError):
        S.tick_item(T, num, "cbfc")                                              # auto lines can't be ticked by hand
    with pytest.raises(S.FilmError):
        S.set_cbfc(T, num, "UA13", "DIL/2/123/2026", "20-10-2026", actor="staff:s1")
    S.set_cbfc(T, num, "UA13", "DIL/2/123/2026", "20-10-2026")
    S.right_add(T, num, "song", "Baarish ka gaana (sync)", "Raag Music", "licensed", sync=True, platforms=["youtube", "theatrical"],
                file_id=_file("licence.pdf", b"%PDF-1.4 licence"))
    from app.db import session
    from app.filmdesk.models import FilmRight
    with session() as s:                                                     # drop the first (bad) row: she replaced it
        s.delete(s.query(FilmRight).filter_by(title="Baarish ka gaana").one())
    monkeypatch.setattr(S, "studio_state", lambda tenant, name: {"outputs": [{"file_id": "vid1", "seconds": 42, "at": "x"}]})
    for k in ("credits", "yt_altered", "yt_kids"):
        S.tick_item(T, num, k)
    with pytest.raises(S.FilmError):
        S.release_request(T, num)                                               # accessibility line not ticked
    with pytest.raises(S.FilmError):
        S.release_request(T, num, force=["access"], reason="CC files distributor bana raha", actor="staff:s1")
    card = S.release_request(T, num, force=["access"], reason="CC files distributor bana raha")["card"]
    assert card["status"] == "waiting" and card["kind"] == "release" and ("filmdesk_card" in [k for k, _ in S.EVENTS])
    assert S.release_request(T, num, force=["access"], reason="CC files distributor bana raha")["existing"]
    with pytest.raises(S.FilmError):
        S.decide(T, card["id"], True, card["hash"])                              # not from her tap
    with pytest.raises(S.FilmError):
        S.decide(T, card["id"], True, "bad", by_tap=True)
    out = S.decide(T, card["id"], True, card["hash"], by_tap=True)
    assert out["card"]["status"] == "approved" and out["file_id"] and S.STORED[-1][1].startswith(b"%PDF")
    v = S.project_view(T, num)
    assert v["status"] == "released" and v["released"]["forced"] == ["access"]
    # message card: consent request to a person, stale after a change, blanks block
    S.person_add(T, "Ritu Sharma", "actor", "9822012345")
    m = S.message_request(T, num, "consent_request", person="P-001", uses=["ai_likeness"])
    assert m["card"]["show"]["blanks"]
    with pytest.raises(S.FilmError):
        S.decide(T, m["card"]["id"], True, m["card"]["hash"], by_tap=True)       # [shartein] still blank
    m = S.message_request(T, num, "consent_request", person="P-001", uses=["ai_likeness", "ai_voice"],
                          terms="2 din ki shooting, fees ₹5,000 (aapse baat ke mutabik)")
    S.project_update(T, num, title="Baarish Wali Chai 2")                       # change after the card
    with pytest.raises(S.FilmError):
        S.decide(T, m["card"]["id"], True, m["card"]["hash"], by_tap=True)
    assert S.card_view(T, m["card"]["id"])["status"] == "stale"
    m = S.message_request(T, num, "consent_request", person="P-001", uses=["ai_likeness"], terms="fees aapse baat karke")
    d = S.decide(T, m["card"]["id"], True, m["card"]["hash"], by_tap=True)
    assert d["draft"]["wa"].startswith("https://wa.me/919822012345") and "khud" in d["say"]
    n = S.message_request(T, num, "custom", phone="9811122233", text="Screener link bhej rahe hain")
    assert S.decide(T, n["card"]["id"], False, n["card"]["hash"], "abhi nahi", by_tap=True)["card"]["status"] == "rejected"


def test_forget_worker_tools_and_api(fd):
    S = fd
    num = _film(S)
    S.person_add(T, "Ritu Sharma", "actor", "9822012345")
    S.cast_set(T, num, "Meena", person="P-001")
    with pytest.raises(S.FilmError):
        S.forget_person(T, "P-001")                                              # still cast in a live film
    S.consent_record(T, "P-001", "signed_form", _file(), ["ai_likeness"], until="2026-11-01")
    S.save_settings(T, morning_time="09:00")
    out = S.tick(NOW)
    kinds = [k for k, _ in S.EVENTS]
    assert out["alerts"] == 1 and "filmdesk_alert" in kinds and out["morning"] == 1 and "filmdesk_day" in kinds
    assert S.tick(NOW)["alerts"] == 0                                            # once each
    S.consent_withdraw(T, "P-001")
    S.forget_person(T, "P-001")
    pv = S.person_view(T, "P-001")
    assert pv["forgotten"] and pv["phone"] == "" and "hataya" in pv["name"] and pv["history"]
    assert not (S._home(T) / "consent" / "P-001").exists()

    from app.agent.filmdesk_tools import FILMDESK_HANDLERS, FILMDESK_TOOLS
    from app.agent.tools import ToolError
    assert {t["name"] for t in FILMDESK_TOOLS} == {"film_desk", "film_desk_dekho"} == set(FILMDESK_HANDLERS)
    for t in FILMDESK_TOOLS:
        assert set(t["input_schema"]["required"]) <= set(t["input_schema"]["properties"])
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(FILMDESK_HANDLERS[tool](ctx, **a))  # noqa: E731
    p = run("film_desk", action="new", title="Diwali ad", logline="Ek mithai dukaan ka Diwali ad", format="ad")
    pn = p["project"]["number"]
    run("film_desk", action="script_set", project=pn, text=SCRIPT)
    assert run("film_desk", action="shots", project=pn)["made"] >= 3
    assert run("film_desk_dekho", what="release", project=pn)["blockers"]
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    for a in ({"action": "consent", "person": "P-001", "how": "video", "file_id": "x", "uses": ["ai_likeness"]},
              {"action": "rating", "project": pn, "rating": "U"}, {"action": "forget", "person": "P-001"}):
        with pytest.raises(ToolError):
            asyncio.run(FILMDESK_HANDLERS["film_desk"](staff, **a))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(FILMDESK_HANDLERS["film_desk"](cust, action="new", title="X"))
    sent = run("film_desk", action="message", project=pn, msg_kind="custom", phone="9811122233", text="Script padh lijiye")
    assert sent["status"] == "needs_tap"
    assert run("film_desk_dekho", what="cards")["cards"]

    from app.filmdesk.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/filmdesk").status_code == 200
    assert c.get(f"/api/filmdesk/projects/{pn}").json()["shots_n"] >= 3
    assert c.put(f"/api/filmdesk/projects/{pn}/rating", json={"rating": "UA13", "descriptors": "halki maar-peet"}).status_code == 200
    cid, h = sent["card"]["id"], sent["card"]["hash"]
    assert c.post(f"/api/filmdesk/cards/{cid}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    ok = c.post(f"/api/filmdesk/cards/{cid}/decide", json={"yes": True, "hash": h})
    assert ok.status_code == 200 and ok.json()["draft"]["wa"].startswith("https://wa.me/91")
    up = c.post("/api/filmdesk/people", json={"name": "Anil Rao", "role": "voice"}).json()["person"]["number"]
    r = c.post(f"/api/filmdesk/people/{up}/consent/upload", files={"file": ("haan.jpg", _photo(), "image/jpeg")},
               data={"how": "video", "uses": "ai_voice,promo"})
    assert r.status_code == 200 and c.get(f"/api/filmdesk/people/{up}").json()["consent"]["status"] == "recorded"
    assert c.post(f"/api/filmdesk/projects/{pn}/storyboard").status_code == 200
    assert c.get(f"/api/filmdesk/projects/{pn}/budget").json()["total"]["draft"]["inr"] > 0
    assert c.put("/api/filmdesk/settings", json={"morning_time": "9 baje"}).status_code == 400
