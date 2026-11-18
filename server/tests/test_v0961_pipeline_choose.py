"""v0.961 HOOLA PIPELINE P1 - kinds + levels + choose + hand-over as pure code (plan sections 3-5).

Every rule in 3-5 has a test here; the same inputs always give the same model. No model call, no network.
"""
from __future__ import annotations

import copy
import json

import pytest

from app.pipeline import box as B
from app.pipeline import choose as C
from app.pipeline import detect as D
from app.pipeline import feed as F
from app.pipeline import handover as H
from app.pipeline import levels as L


def _m(mid, pts, route="openrouter", status="ready"):
    return {"id": mid, "route": route, "status": status, "points": pts, "name": mid}


def _table(prefix_levels):
    return {"levels": prefix_levels, "n": sum(len(v) for v in prefix_levels.values()), "method": "bands",
            "boards": ["text/overall"], "warnings": []}


TEXT = {"ins": ["text"], "outs": ["text"], "tools": True, "ctx": 200_000, "structured": True}


def doc():
    chat = _table({
        "ULTRA": [_m("a/ultra1", 3), _m("b/ultra2", 10)],
        "MAX": [_m("a/max1", 30), _m("b/max2", 35), _m("c/max3", 40)],
        "HIGH": [_m("a/high1", 55), _m("a/high2", 60), _m("b/high3", 62), _m("c/high4", 70)],
        "MID": [_m("a/mid1", 85), _m("b/mid2", 90), _m("c/mid3", 100)],
        "LOW": [_m("a/low1", 130), _m("b/low2", 140)],
    })
    img = _table({"ULTRA": [_m("o/img-u", 1)], "MAX": [_m("o/img-m", 30)], "HIGH": [], "MID": [],
                  "LOW": [_m("o/img-l", 150)]})
    wl = _table({"ULTRA": [], "MAX": [], "HIGH": [_m("a/wl-h", 60)], "MID": [_m("b/wl-m", 90)], "LOW": []})
    wl["by_language"] = {"spanish": _table({"ULTRA": [], "MAX": [], "HIGH": [_m("es/high", 55)],
                                            "MID": [_m("es/mid", 85)], "LOW": []})}
    models = {m["id"]: dict(TEXT) for lv in chat["levels"].values() for m in lv}
    models.update({"a/wl-h": dict(TEXT), "b/wl-m": dict(TEXT), "es/high": dict(TEXT), "es/mid": dict(TEXT)})
    for k in ("o/img-u", "o/img-m", "o/img-l"):
        models[k] = {"ins": ["text", "image"], "outs": ["image"], "tools": False, "ctx": 0}
    return {"read_on": "2026-11-16", "models": models,
            "tables": {"chat": chat, "reason": copy.deepcopy(chat), "tools": copy.deepcopy(chat),
                       "code": copy.deepcopy(chat), "research": copy.deepcopy(chat), "image.make": img,
                       "write.lang": wl, "route": {"same_as": "chat"}, "translate": {"same_as": "write.lang"},
                       "embed": {"not_ranked": "keeps its own embedder"}}}


# ------------------------------------------------------------------ 3.1 start level
@pytest.mark.parametrize("kind,start", [("route", "LOW"), ("extract", "LOW"), ("summarise", "LOW"),
                                        ("chat", "MID"), ("write", "MID"), ("image.make", "MID"),
                                        ("reason", "HIGH"), ("tools", "HIGH"), ("code", "HIGH"),
                                        ("facts", "HIGH"), ("video.make", "HIGH"), ("unknown.kind", "MID")])
def test_start_level(kind, start):
    assert L.level_for(kind, [])["level"] == start


def test_indian_writing_starts_high_other_languages_mid():
    assert L.start_level("write.lang", "hi") == "HIGH"
    assert L.start_level("write.lang", "ta") == "HIGH"
    assert L.start_level("write.lang", "es") == "MID"


# ------------------------------------------------------------------ 3.2 signals: one level each
@pytest.mark.parametrize("sig", ["hard", "big", "costly", "exact", "deep_research", "failed_check"])
def test_each_signal_raises_one_level(sig):
    assert L.level_for("chat", [sig])["level"] == "HIGH"


def test_signals_read_from_her_words():
    assert "costly" in L.signals("Mere customers ko GST invoice bhejo", hard=False)
    assert "exact" in L.signals("Is product ka price kitna hai?", hard=False)
    assert "big" in L.signals("x", parts=3, hard=False)
    assert "big" in L.signals("x", input_words=500, hard=False)
    assert "failed_check" in L.signals("x", failed_check=True, hard=False)
    assert L.signals("hi", hard=False) == []


def test_a_signal_that_made_the_kind_does_not_raise_it():
    assert L.for_kind("reason", ["hard", "exact", "costly"]) == ["costly"]
    assert L.for_kind("research", ["hard", "exact"]) == []          # plan 11: five-company research stays MID


# ------------------------------------------------------------------ 3.3 limits
def test_her_choice_wins():
    assert L.level_for("reason", ["hard", "costly"], her_level="low")["level"] == "LOW"
    assert L.level_for("chat", [], her_level="ULTRA", call_waiting=True)["level"] == "ULTRA"
    with pytest.raises(ValueError):
        L.level_for("chat", [], her_level="TOP")


def test_call_caps_a_waited_part_at_high():
    r = L.level_for("tools", ["costly", "exact"], call_waiting=True)
    assert r["level"] == "HIGH" and any("live call" in w for w in r["why"])
    assert L.level_for("tools", ["costly", "exact"])["level"] == "MAX"      # background: no cap


def test_ultra_only_when_allowed():
    assert L.level_for("reason", ["exact", "big"])["level"] == "MAX"             # signals alone stop at MAX
    assert L.level_for("reason", ["hard", "costly"])["level"] == "ULTRA"         # hard AND costly
    assert L.level_for("chat", [], her_ultra=True)["level"] == "ULTRA"           # she asked
    assert L.level_for("chat", [], max_failed=True)["level"] == "ULTRA"          # a MAX try failed the check


def test_level_never_goes_down_inside_a_message():
    r = L.level_for("chat", [], floor="MAX")
    assert r["level"] == "MAX" and "never lower" in r["why"][-1]
    assert L.up_one("ULTRA") == "ULTRA" and L.up_one("LOW") == "MID"


# ------------------------------------------------------------------ 4 step 1: remove what cannot do the part
def _need(**k):
    return {"kind": "chat", "level": "HIGH", "surface": "chat", **k}


def test_not_ready_route_is_removed():
    d = doc()
    d["tables"]["chat"]["levels"]["HIGH"][0]["status"] = "check_terms"
    r = C.choose(d, _need())
    assert r["model"]["id"] != "a/high1" and "not ready" in r["dropped"]["a/high1"]


def test_wrong_input_output_tools_window_removed():
    d = doc()
    d["models"]["a/high1"]["outs"] = ["image"]
    d["models"]["a/high2"]["tools"] = False
    d["models"]["b/high3"]["ctx"] = 8000
    r = C.choose(d, _need(kind="tools", size_tokens=10_000))
    assert r["model"]["id"] == "c/high4"
    assert "cannot give text" in r["dropped"]["a/high1"]
    assert "tools" in r["dropped"]["a/high2"]
    assert "window" in r["dropped"]["b/high3"]


def test_image_input_needed():
    d = doc()
    d["tables"]["read.image"] = copy.deepcopy(d["tables"]["chat"])
    d["models"]["a/high1"]["ins"] = ["text", "image"]
    r = C.choose(d, _need(kind="read.image"))
    assert r["model"]["id"] == "a/high1"


def test_paused_and_route_and_company_rules():
    d = doc()
    r = C.choose(d, _need(), health={"a/high1": {"paused": True}})
    assert r["model"]["id"] != "a/high1" and "paused" in r["dropped"]["a/high1"]
    r = C.choose(d, _need(block=["a"]))
    assert r["model"]["id"].split("/")[0] != "a"
    r = C.choose(d, _need(routes=["fal"]))
    assert r["model"] is None


# ------------------------------------------------------------------ 4 step 2 + 3: rank, one main + two backups
def test_rank_by_score_when_no_record_and_backups_from_other_companies():
    r = C.choose(doc(), _need())
    assert r["model"]["id"] == "a/high1"
    assert [b["id"] for b in r["backups"]] == ["b/high3", "c/high4"]          # a/high2 skipped: same company


def test_surface_weights():
    health = {"a/high1": {"ok_rate": 0.80, "first_word_s": 9}, "b/high3": {"ok_rate": 1.0, "first_word_s": 1},
              "a/high2": {"ok_rate": 1.0, "first_word_s": 7}, "c/high4": {"ok_rate": 0.99, "first_word_s": 0.4}}
    assert C.choose(doc(), _need(surface="call"), health=health)["model"]["id"] == "c/high4"       # speed first
    assert C.choose(doc(), _need(surface="code"), health=health)["model"]["id"] == "a/high1"       # score first
    assert C.choose(doc(), _need(surface="background"), health=health)["model"]["id"] == "a/high2"  # reliability


def test_same_inputs_same_choice_and_snapshot():
    d = doc()
    a = C.choose(d, _need(level="MID"))
    assert all(C.choose(copy.deepcopy(d), _need(level="MID")) == a for _ in range(5))
    held = C.snapshot(d)
    d["tables"]["chat"]["levels"]["MID"].reverse()          # a table refresh while the message runs
    assert C.choose(held, _need(level="MID")) == a


def test_empty_level_uses_nearest_filled_level_above():
    r = C.choose(doc(), {"kind": "image.make", "level": "MID"})
    assert r["level_used"] == "MAX" and r["model"]["id"] == "o/img-m"
    assert any("used MAX" in w for w in r["why"])


def test_ultra_is_one_model_backups_from_max():
    r = C.choose(doc(), _need(level="ULTRA"))
    assert r["model"]["id"] == "a/ultra1"
    assert {b["level"] for b in r["backups"]} == {"MAX"}
    assert all(b["id"] != "b/ultra2" for b in r["backups"])


def test_language_views():
    r = C.choose(doc(), {"kind": "write.lang", "level": "HIGH", "language": "es"})
    assert r["model"]["id"] == "es/high"
    r = C.choose(doc(), {"kind": "translate", "level": "HIGH", "language": "mr"})
    assert r["model"]["id"] == "a/wl-h" and any("thin" in w for w in r["why"])


def test_same_as_and_not_ranked():
    r = C.choose(doc(), {"kind": "route", "level": "LOW"})
    assert r["table"] == "chat" and r["model"]["id"] == "a/low1"
    r = C.choose(doc(), {"kind": "embed", "level": "LOW"})
    assert r["model"] is None and "embedder" in " ".join(r["why"])


def test_her_pick_is_a_pin_for_what_it_can_do():
    r = C.choose(doc(), _need(pin="openrouter:b/mid2"))
    assert r["model"]["id"] == "b/mid2" and len(r["backups"]) == 2
    r = C.choose(doc(), {"kind": "image.make", "level": "MAX", "pin": "a/high1"})
    assert r["model"]["id"] == "o/img-m" and any("cannot do this part" in w for w in r["why"])


# ------------------------------------------------------------------ 5.1 same model for 30 minutes
def test_sticky_for_thirty_minutes_while_healthy():
    st = {"id": "b/high3", "at": 1000.0}
    assert C.choose(doc(), _need(), sticky=st, now=1000 + 29 * 60)["model"]["id"] == "b/high3"
    assert C.choose(doc(), _need(), sticky=st, now=1000 + 31 * 60)["model"]["id"] == "a/high1"
    r = C.choose(doc(), _need(), sticky=st, now=1100, health={"b/high3": {"paused": True}})
    assert r["model"]["id"] == "a/high1"
    B._STICKY.clear()
    B.remember("chat1", "chat", "HIGH", "b/high3", now=50)
    assert B.recall("chat1", "chat", "HIGH", now=60)["id"] == "b/high3"
    assert B.recall("chat1", "chat", "HIGH", now=50 + 31 * 60) is None


# ------------------------------------------------------------------ 5.2 + 5.3 hand-over
def test_first_word_limits():
    assert (H.first_word_limit("call"), H.first_word_limit("chat"), H.first_word_limit("background")) == (3, 25, 30)
    assert H.late("call", 3.1) and not H.late("chat", 24.9)


@pytest.mark.parametrize("ev", ["error", "refusal", "empty"])
def test_failure_goes_to_backup_same_level(ev):
    p = H.new_part("chat", "MID")
    mv = H.next_move(p, ev)
    assert mv["action"] == "backup" and mv["level"] == "MID" and mv["backup"] == 0


def test_late_first_word_backup_and_race_on_a_call():
    assert H.next_move(H.new_part("chat", "MID"), "late")["action"] == "backup"
    mv = H.next_move(H.new_part("chat", "MID", "call"), "late")
    assert mv["action"] == "race" and mv["after_s"] == 3


def test_failed_check_moves_up_once_then_delivers():
    p = H.new_part("write", "MID")
    mv = H.next_move(p, "failed_check", problems=["figure 42 not in the facts"])
    assert mv == {"action": "up", "level": "HIGH", "from": "MID", "problems": ["figure 42 not in the facts"]}
    assert H.next_move(p, "failed_check")["action"] == "deliver"


def test_too_long_and_asked_for_better():
    assert H.next_move(H.new_part("chat", "MID"), "too_long", size_tokens=900_000)["action"] == "bigger"
    p = H.new_part("chat", "MID")
    assert H.next_move(p, "better")["level"] == "HIGH" and p["level"] == "HIGH"
    top = H.new_part("chat", "ULTRA")
    assert H.next_move(top, "better")["action"] == "deliver"


def test_at_most_two_changes_never_a_loop():
    p = H.new_part("chat", "MID")
    H.next_move(p, "error")
    H.next_move(p, "late")
    assert H.next_move(p, "error")["action"] == "stop"
    assert H.next_move(p, "failed_check")["action"] == "deliver"
    with pytest.raises(ValueError):
        H.next_move(H.new_part("chat", "MID"), "boom")


# ------------------------------------------------------------------ section 2: kind + language by code
@pytest.mark.parametrize("text,att,kind", [
    ("hi", None, "chat"),
    ("Is photo ka background white kar do", [{"type": "image/png"}], "image.edit"),
    ("What is in this picture?", [{"type": "image/jpeg"}], "read.image"),
    ("Is PDF ka summary do", [{"type": "application/pdf"}], "summarise"),
    ("", [{"name": "bill.pdf"}], "read.pdf"),
    ("", [{"type": "audio/ogg"}], "speech.in"),
    ("Ek Diwali sale ka poster banao", None, "image.make"),
    ("A 15 second reel for my bakery", None, "video.make"),
    ("Make a jingle for my shop", None, "music.make"),
    ("Mujhe kal 9 baje remind kar do", None, "tools"),
    ("Translate this letter into Marathi", None, "translate"),
    ("Write a letter to my landlord", None, "write"),
    ("Hindi mein report likho EV par", None, "write.lang"),
    ("Research the top 5 EV makers in India", None, "research"),
    ("Write a regex for Indian PIN codes", None, "code.small"),
])
def test_kind_by_code(text, att, kind):
    assert D.kind(text, att)["kind"] == kind


def test_language_detection():
    assert D.language("Kal ka mausam kaisa rahega?") == "hinglish"
    assert D.language("मुझे एक रिपोर्ट चाहिए") == "hi"
    assert D.language("मला एक अहवाल हवा आहे") == "mr"
    assert D.language("Write this in Tamil") == "ta"
    assert D.language("What is the weather today") == "en"
    assert D.kind("Fix it", surface="code")["kind"] == "code"
    assert D.kind("hi")["parts"] == 1 and D.kind("Find prices, and then make a table; then a PDF")["parts"] >= 3


# ------------------------------------------------------------------ the feed keeps what each model can do
def test_feed_saves_model_abilities():
    tables = {"chat": {"levels": {"MID": [_m("a/x", 1), _m("fal-id", 2, route="fal")]}},
              "write.lang": {"levels": {}, "by_language": {"spanish": {"levels": {"MID": [_m("b/y", 1)]}}}}}
    by_id = {"a/x": {"context_length": 1000, "architecture": {"input_modalities": ["text", "image"],
                                                             "output_modalities": ["text"]},
                     "supported_parameters": ["tools", "response_format"]},
             "b/y": {"context_length": 50, "architecture": {}, "supported_parameters": []}}
    info = F.models_info(tables, by_id)
    assert info["a/x"] == {"ctx": 1000, "ins": ["image", "text"], "outs": ["text"], "tools": True,
                           "structured": True}
    assert "b/y" in info and "fal-id" not in info


# ------------------------------------------------------------------ the Box end to end + the preview route
def test_box_end_to_end_and_switch_off():
    from app.config import get_settings
    assert get_settings().pipeline_on is False          # nothing is routed through the Box until P7
    B._STICKY.clear()
    r = B.choose_for("Agar 3 machine 5 din mein 120 piece banati hain to 7 machine 9 din mein kitne?", doc=doc())
    assert r["kind"] == "reason" and r["level"] == "HIGH" and r["model"]["id"] == "a/high1"
    r = B.choose_for("Mujhe kal 9 baje remind kar do", surface="call", doc=doc())
    assert r["kind"] == "tools" and r["level"] == "HIGH"


def test_preview_route(env, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.pipeline import store
    monkeypatch.setattr(store, "read_current", lambda: doc())
    c = TestClient(app)
    h = {}
    r = c.get("/api/pipeline/choose", params={"text": "Mere customers ko GST reminder bhej do"}, headers=h)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ready"] and j["kind"] == "tools" and j["level"] == "MAX" and j["model"]["id"] == "a/max1"
    assert c.get("/api/pipeline/choose", params={"text": "x", "surface": "moon"}, headers=h).status_code == 422
    assert json.dumps(j)
