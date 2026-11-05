"""Film Desk DELIVERY layer (register docs/research/film_industry #64 deliverables manager, #93 subtitle + dub localisation PM, #107/#110
digital-replica consent): a deliverables tracker and a localisation tracker in CODE. Honest by construction: the starter list is only a list
of ITEM NAMES (the buyer's own spec is final, said in every view), dates/vendors/statuses are hers, and the single check it makes alone is the
consent register - an AI-voice dub must name a person whose recorded consent covers ai_voice today (withdrawn, expired, missing, famous or
unknown person = flagged). Nothing is translated, dubbed, sent or accepted."""
import asyncio
from datetime import date

import pytest

import app.filmdesk.models  # noqa: F401
from app.filmdesk import delivery as DL
from tests.test_film_production_layer import BIG
from tests.test_kala_filmdesk import T, _file, fd  # noqa: F401
from tests.test_life import conv_ctx

TODAY = date(2026, 11, 10)


# ---------------------------------------------------------------- deliverables (pure)
def test_deliverable_normalising_and_errors():
    d = DL.norm_deliverable({"label": "  Video   master ", "buyer": "Platform A", "due": "2026-12-01", "status": "IN_PROGRESS"}, 2)
    assert d["id"] == "d2" and d["label"] == "Video master" and d["status"] == "in_progress" and d["due"] == "2026-12-01"
    assert DL.norm_deliverable({"label": "X", "due": "soon"}, 1)["due"] == ""                    # a bad date is blank, not guessed
    for bad in ({"label": ""}, {"label": "X", "status": "shipped"}):
        with pytest.raises(ValueError):
            DL.norm_deliverable(bad, 1)


def test_starter_lists_are_names_only_and_say_so():
    assert "Video master" in DL.starter_items("ott") and "DCP (cinema package)" in DL.starter_items("theatrical")
    assert DL.starter_items(" Festival ")[0].startswith("Screener")
    with pytest.raises(ValueError):
        DL.starter_items("radio")
    v = DL.deliverables_view([DL.norm_deliverable({"label": "A"}, 1)], TODAY)
    assert "apni specification final" in v["note"]


def test_deliverables_view_flags_progress_and_sorting():
    items = [DL.norm_deliverable(x, i) for i, x in enumerate([
        {"label": "Late", "due": "2026-11-01"}, {"label": "Soon", "due": "2026-11-14", "status": "in_progress"},
        {"label": "Far", "due": "2027-03-01"}, {"label": "Done", "due": "2026-10-01", "status": "accepted"},
        {"label": "Failed", "due": "2026-12-01", "status": "qc_failed"}, {"label": "Waived", "status": "waived"}], 1)]
    v = DL.deliverables_view(items, TODAY)
    msgs = " | ".join(v["flags"])
    assert "Late: due 2026-11-01 nikal chuki (9 din)" in msgs and "Soon: 4 din me due" in msgs and "Failed: QC fail" in msgs
    assert "Done" not in msgs and "Waived" not in msgs and "Far" not in msgs                       # finished and far-off items are quiet
    assert v["total"] == 6 and v["done"] == 2 and v["progress_pct"] == 33.3 and v["counts"]["qc_failed"] == 1
    assert [r["label"] for r in v["deliverables"]][:2] == ["Late", "Soon"]                           # open and earliest-due first
    assert DL.deliverables_view([], TODAY)["progress_pct"] == 0.0


# ---------------------------------------------------------------- localisation (pure)
def test_loc_normalising_dub_mode_rules():
    sub = DL.norm_loc({"language": "tamil", "kind": "subtitles", "dub_mode": "ai_voice"}, 1)
    assert sub["language"] == "Tamil" and sub["dub_mode"] == "" and sub["kind"] == "subtitles"      # subtitles never carry a voice mode
    assert DL.norm_loc({"language": "Hindi", "kind": "dub"}, 2)["dub_mode"] == "human"              # a dub defaults to a human voice, not an AI one
    assert DL.norm_loc({"language": "Hindi", "kind": "both", "dub_mode": "AI_VOICE"}, 3)["dub_mode"] == "ai_voice"
    assert DL.norm_loc({"language": "Hindi", "qa_rounds": "-4"}, 4)["qa_rounds"] == 0
    for bad in ({"language": ""}, {"language": "X", "kind": "karaoke"}, {"language": "X", "status": "ok"}):
        with pytest.raises(ValueError):
            DL.norm_loc(bad, 1)


def test_loc_view_flags_and_consent_hook():
    calls = []

    def check(ref):
        calls.append(ref)
        return "Ritu ki ijazat darj nahi hai." if ref == "P-001" else ""
    items = [DL.norm_loc(x, i) for i, x in enumerate([
        {"language": "tamil", "kind": "dub", "dub_mode": "ai_voice", "voice_person": "P-001", "due": "2026-11-12"},
        {"language": "telugu", "kind": "dub", "dub_mode": "ai_voice"},
        {"language": "bengali", "kind": "both", "dub_mode": "ai_voice", "voice_person": "P-002", "status": "recording"},
        {"language": "marathi", "kind": "subtitles", "status": "blocked", "due": "2026-11-01"},
        {"language": "urdu", "kind": "subtitles", "qa_rounds": 3, "status": "qc"},
        {"language": "english", "kind": "subtitles", "status": "accepted", "due": "2026-10-01"}], 1)]
    v = DL.loc_view(items, TODAY, check)
    msgs = " | ".join(v["flags"])
    assert "Tamil (dub): AI awaaz roki gayi: Ritu ki ijazat" in msgs and "Tamil (dub): 2 din me due" in msgs
    assert "Telugu (dub): AI awaaz roki gayi: AI awaaz kiski hai" in msgs                              # no person named = blocked without asking the register
    assert "Bengali" not in msgs and calls == ["P-001", "P-002"]                                       # consent ok: no flag; hook asked only for named people
    assert "Marathi (subtitles): ruka hua hai" in msgs and "Marathi (subtitles): due 2026-11-01 nikal chuki" in msgs
    assert "Urdu (subtitles): 3 QA round" in msgs and "English" not in msgs
    assert v["ai_voice_blocked"] == 2 and v["total"] == 6 and v["done"] == 1
    assert "na anuvaad karta hai na dubbing" in v["note"]
    assert DL.loc_view(items, TODAY, None)["ai_voice_blocked"] == 1                                    # no hook: only the unnamed-voice case is certain


# ---------------------------------------------------------------- service + tools
def _film(S):
    p = S.project_new(T, title="Chai Aur Patang", logline="Ek chai wali aur ek bachcha, patang ke bahane dosti", fmt="short")
    num = p["project"]["number"]
    S.script_set(T, num, BIG)
    return num


def test_service_deliverables_flow(fd, monkeypatch):
    S = fd
    monkeypatch.setattr(S, "today", lambda tenant: TODAY)
    num = _film(S)
    r = S.deliverable_op(T, num, "starter", kind="ott", buyer="Platform A", due="2026-12-15")
    assert r["total"] == 11 and "11 item jude" in r["say"] and all(x["buyer"] == "Platform A" for x in r["deliverables"])
    again = S.deliverable_op(T, num, "starter", kind="ott")                                             # nothing doubles up
    assert again["total"] == 11 and "0 item jude" in again["say"]
    S.deliverable_op(T, num, "starter", kind="festival")                                                # overlap by name is skipped, the rest join
    assert S.deliverables_view(T, num)["total"] > 11
    one = S.deliverables_view(T, num)["deliverables"][0]
    S.deliverable_op(T, num, "update", entry=one["id"], status="accepted")
    assert S.deliverables_view(T, num)["done"] == 1
    S.deliverable_op(T, num, "add", label="Poster (extra)", due="2026-11-12")
    assert any("Poster (extra)" in f and "2 din me due" in f for f in S.deliverables_view(T, num)["flags"])
    S.deliverable_op(T, num, "remove", entry=one["id"])
    ids = [x["id"] for x in S.deliverables_view(T, num)["deliverables"]]
    assert one["id"] not in ids
    new = S.deliverable_op(T, num, "add", label="Later item")["deliverables"]
    assert len({x["id"] for x in new}) == len(new)                                                       # ids never collide after a removal
    with pytest.raises(S.FilmError):
        S.deliverable_op(T, num, "update", entry="d999", status="todo")
    with pytest.raises(S.FilmError):
        S.deliverable_op(T, num, "starter", kind="radio")
    with pytest.raises(S.FilmError):
        S.deliverable_op(T, num, "add", label="")


def test_service_ai_voice_follows_the_consent_register(fd, monkeypatch):
    S = fd
    monkeypatch.setattr(S, "today", lambda tenant: TODAY)
    num = _film(S)
    ritu = S.person_add(T, "Ritu Sharma", "actor", "98220 12345")["person"]
    assert ritu["number"] == "P-001"
    S.localise_op(T, num, "add", language="tamil", kind="dub", dub_mode="ai_voice", voice_person="P-001", due="2026-12-01")
    v = S.localisation_view(T, num)
    assert v["ai_voice_blocked"] == 1 and "ijazat" in v["localisation"][0]["voice_check"]               # no consent recorded yet
    S.consent_record(T, "P-001", "signed_form", _file(), ["ai_likeness"], until="2027-12-31")           # likeness only, not voice
    assert "awaaz" in S.localisation_view(T, num)["localisation"][0]["voice_check"]
    S.consent_record(T, "P-001", "video", _file("haan.jpg"), ["ai_voice"], until="2027-12-31")
    v = S.localisation_view(T, num)
    assert v["ai_voice_blocked"] == 0 and not v["flags"]
    S.consent_withdraw(T, "P-001", "wapas")                                                              # withdrawal after the fact is caught
    v = S.localisation_view(T, num)
    assert v["ai_voice_blocked"] == 1 and any("wapas" in f for f in v["flags"])
    S.localise_op(T, num, "add", language="telugu", kind="dub", dub_mode="ai_voice", voice_person="P-077")
    assert any("register me vyakti nahi mila" in f for f in S.localisation_view(T, num)["flags"])
    star = S.person_add(T, "Virat Kohli", "actor")["person"]
    S.localise_op(T, num, "add", language="kannada", kind="dub", dub_mode="ai_voice", voice_person=star["number"])
    assert any("personality" in f for f in S.localisation_view(T, num)["flags"])                        # famous people are never cleared for an AI voice
    S.localise_op(T, num, "update", entry="l1", dub_mode="human")                                         # switching to a human dubber clears the flag
    assert not any("Tamil" in f and "roki" in f for f in S.localisation_view(T, num)["flags"])


def test_tools_expose_the_delivery_layer(fd, monkeypatch):
    from app.agent import filmdesk_tools as FT
    from app.agent.tools import ToolError
    S = fd
    monkeypatch.setattr(S, "today", lambda tenant: TODAY)
    assert {"deliverable", "localise"} <= set(FT._ACTIONS) and not ({"deliverable", "localise"} & FT._OWNER_ONLY)
    props = FT.FILMDESK_TOOLS[0]["input_schema"]["properties"]
    assert {"label", "buyer", "due", "dub_mode", "voice_person", "vendor", "qa_rounds"} <= set(props)
    num = _film(S)
    ctx = conv_ctx()
    d = asyncio.run(FT._film_desk(ctx, action="deliverable", project=num, op="starter", kind="tv", buyer="Channel X"))
    assert d["total"] == 7
    assert asyncio.run(FT._film_desk_dekho(ctx, what="deliverables", project=num))["done"] == 0
    loc = asyncio.run(FT._film_desk(ctx, action="localise", project=num, op="add", language="hindi", kind="subtitles", due="2026-11-12"))
    assert loc["localisation"][0]["language"] == "Hindi"
    assert asyncio.run(FT._film_desk_dekho(ctx, what="localisation", project=num))["total"] == 1
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    assert asyncio.run(FT._film_desk(staff, action="deliverable", project=num, op="add", label="Staff item"))["total"] == 8       # the crew may keep it
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(FT._film_desk(cust, action="localise", project=num, op="add", language="x"))
