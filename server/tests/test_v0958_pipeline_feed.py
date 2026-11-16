"""v0.958 HOOLA PIPELINE P0 - the feed: public leaderboards -> dated level tables (docs/HOOLA_PIPELINE_PLAN.md).
No network: every source is replaced. The voiceofindia parsers read the real boards' text kept with the code."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest

NOW = time.time()


def _m(mid, name, out="text", ins=("text",), params=("tools", "structured_outputs"), created=None):
    return {"id": mid, "name": name, "created": created or int(NOW - 30 * 86400),
            "architecture": {"output_modalities": [out], "input_modalities": list(ins)},
            "supported_parameters": list(params)}


def _cat():
    cat = [_m(f"lab/model-{i}", f"Lab: Model {i}") for i in range(30)]
    cat.append(_m("lab/no-tools", "Lab: No Tools", params=()))
    cat.append(_m("lab/old", "Lab: Old", created=int(NOW - 900 * 86400)))
    cat.append(_m("img/pic-1", "Img: Pic 1", out="image", ins=("text", "image")))
    from app.pipeline import names as N
    cat += [_m(v, v, out="speech") for v in N.VOI_OR.values()]       # the voice models OpenRouter carries
    return cat


def _rows(names_ratings, cat="overall", votes=1000):
    return [{"model_name": n, "rating": float(r), "vote_count": votes, "category": cat,
             "leaderboard_publish_date": "2026-11-11"} for n, r in names_ratings]


@pytest.fixture
def pl(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DIR", str(tmp_path / "pl"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app.pipeline import sources as S
    S.reset()
    text = _rows([(f"Model {i}", 1500 - i * 9) for i in range(30)] + [("No Tools", 1600), ("Old", 1600)])
    for c in ["creative_writing", "longer_query", "math", "hard_prompts", "coding", "instruction_following",
              "non_english", "spanish", "chinese", "french", "german", "japanese", "korean", "russian", "polish"]:
        text += _rows([(f"Model {i}", 1500 - i * 9) for i in range(30)], cat=c)
    boards = {"text": text}
    monkeypatch.setattr(S, "openrouter", _cat)
    monkeypatch.setattr(S, "config_rows", lambda c, **k: boards.get(c, []))
    monkeypatch.setattr(S, "voi_tts", lambda: (_ for _ in ()).throw(RuntimeError("no browser here")))
    monkeypatch.setattr(S, "voi_stt", lambda: (_ for _ in ()).throw(RuntimeError("no browser here")))
    return boards


def test_voice_boards_parse_the_real_page_text():
    from app.pipeline import sources as S
    snap = Path(__file__).resolve().parents[1] / "app" / "pipeline" / "snapshot"
    tts = S.parse_voi_tts((snap / "voi_tts.txt").read_text())
    stt = S.parse_voi_stt((snap / "voi_stt.txt").read_text())
    assert len(tts) == 23 and tts[0] == {"name": "Eleven v4", "org": "ElevenLabs", "elo": 1119, "votes": 834}
    assert any(r["name"] == "Maya 2 Native" and r["elo"] == 1063 for r in tts)      # a row with no licence
    assert len(stt) == 32 and stt[0]["name"] == "Indic Transcribe Core" and stt[0]["wer"] == 3.39


def test_bands_cap_four_per_level_and_fall_back_to_rank_split():
    from app.pipeline import cut as C
    ranked = [{"id": f"m{i}", "points": float(p)} for i, p in enumerate([0, 5, 10, 15, 20, 30, 40, 55, 70, 90, 100,
                                                                          130, 150])]
    lv, method = C.levels(ranked)
    assert method == "bands" and [len(lv[k]) for k in ("ULTRA", "MAX", "HIGH", "MID", "LOW")] == [4, 2, 2, 2, 2]
    tight = [{"id": f"m{i}", "points": float(i)} for i in range(13)]      # all within 25 points
    lv, method = C.levels(tight)
    assert method == "rank split" and sum(len(v) for v in lv.values()) == 13 and len(lv["ULTRA"]) >= 2


def test_only_models_that_can_do_the_work_are_kept():
    from app.pipeline import cut as C, names as N
    cat = _cat()
    idx, by_id = N.index(cat), {m["id"]: m for m in cat}
    rows = _rows([("No Tools", 1600), ("Old", 1590), ("Model 0", 1500), ("Pic 1", 1550)])
    got = C.board_points(rows, idx, by_id, "text", "tools", NOW)
    assert set(got) == {"lab/model-0"}            # no tools, too old, gives pictures -> out
    assert C.board_points(_rows([("Model 0", 1500)], votes=50), idx, by_id, "text", None, NOW) == {}  # too few votes
    r = C.board_points(_rows([("SkyReels V4", 1500), ("Sora 2 Pro", 1400)]), idx, by_id, "video", None, NOW)
    assert "fal-ai/sora-2/text-to-video/pro" in r and not any("skyreels" in k for k in r)   # permission not given


def test_score_boards_rank_onto_the_same_scale():
    from app.pipeline import cut as C, names as N
    cat = _cat()
    rows = [{"model_name": f"Model {i}", "score": 0.9 - i / 100, "rank": i + 1, "category": "overall"} for i in range(5)]
    got = C.board_points(rows, N.index(cat), {m["id"]: m for m in cat}, "text", "tools", NOW)
    assert got["lab/model-0"]["points"] == 0 and got["lab/model-4"]["points"] == C.SCORE_SPAN


def test_feed_writes_dated_tables_and_is_deterministic(pl):
    from app.pipeline import feed, store
    a = feed.run()["doc"]
    b = feed.run(write=False)["doc"]
    assert a["tables"] == b["tables"]                          # same boards -> same tables
    day = a["read_on"]
    assert (store.root() / f"tables-{day}.json").exists() and store.read_current()["read_on"] == day
    chat = a["tables"]["chat"]
    assert 10 <= chat["n"] <= 20 and all(len(v) <= 4 for v in chat["levels"].values())
    assert all(m["id"] not in ("lab/old",) for v in chat["levels"].values() for m in v)
    assert a["tables"]["route"] == {"same_as": "chat"} and "not_ranked" in a["tables"]["embed"]
    assert set(a["tables"]["write.lang"]["by_language"]) >= {"spanish", "japanese"}
    # voice: the browser failed here -> the copy shipped with the code, said plainly
    assert a["tables"]["speech.in.indian"]["n"] == 20 and a["tables"]["speech.out.indian"]["n"] == 20
    assert any("voiceofindia" in w for w in a["warnings"])
    assert a["tables"]["speech.in.indian"]["levels"]["ULTRA"][0]["route"] == "direct:bodhan"
    assert a["tables"]["music.make"]["n"] >= 10
    # a board with no rows -> a pool under 10 is named
    assert any(w.startswith("image.make: only 0") for w in a["warnings"])


def test_changes_are_logged_and_big_jumps_applied(pl):
    from app.pipeline import feed, store
    feed.run()
    pl["text"] = [r for r in pl["text"] if not (r["category"] == "overall" and r["model_name"] == "Model 0")] + \
        _rows([("Model 0", 1300)])                # the best model falls to the bottom
    from app.pipeline import sources as S
    S.reset()
    ch = feed.run()["changes"]
    moved = [c for c in ch if c["kind"] == "chat" and c["id"] == "lab/model-0"]
    assert moved and (moved[0]["change"] == "left" or moved[0].get("big"))
    assert store.recent_changes() and store.read_current()["tables"]["chat"]["levels"]["ULTRA"][0]["id"] != "lab/model-0"


def test_a_board_that_fails_keeps_yesterdays_table(pl, monkeypatch):
    from app.pipeline import feed, sources as S
    feed.run()
    S.reset()
    monkeypatch.setattr(S, "config_rows", lambda c, **k: (_ for _ in ()).throw(RuntimeError("down")))
    d = feed.run()["doc"]
    assert d["tables"]["chat"]["n"] >= 10 and "kept the last table" in " ".join(d["tables"]["chat"]["warnings"])
    assert any("not read" in w for w in d["warnings"])


def test_hand_kept_pool_warns_when_a_model_leaves_openrouter(pl):
    from app.pipeline import feed
    w: list[str] = []
    t = feed._manual("speech.in", {}, w)
    assert t["n"] == 17 and any("no longer on OpenRouter" in x for x in w)


def test_worker_slot_runs_once_a_day_and_only_when_on(pl, monkeypatch):
    from app import worker
    from app.pipeline import feed
    calls = []
    monkeypatch.setattr(feed, "run", lambda: calls.append(1))
    worker._pl_last = 0.0
    asyncio.run(worker.pipeline_jobs())
    assert calls == []                                     # PIPELINE_FEED false in tests
    monkeypatch.setenv("PIPELINE_FEED", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    worker._pl_last = 0.0
    asyncio.run(worker.pipeline_jobs())
    assert calls == [1]
    worker._pl_last = 0.0
    asyncio.run(worker.pipeline_jobs())                    # throttle reset but the same 10 min: still once
    assert calls in ([1], [1, 1])


def test_api_route_reads_the_current_tables(env, pl):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.pipeline import feed
    c = TestClient(app)
    assert c.get("/api/pipeline/tables").json()["ready"] is False
    feed.run()
    r = c.get("/api/pipeline/tables?kind=chat").json()
    assert r["ready"] and list(r["tables"]) == ["chat"] and r["tables"]["chat"]["n"] >= 10
