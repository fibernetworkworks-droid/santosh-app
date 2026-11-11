"""v0.496.0 OFFICE HOURS - the THINK/PLAN lane (our own gstack, house-sized).

Owner: "BUILD", straight after "NOW READ THIS REPO FIRST" on github.com/garrytan/gstack (Garry Tan's
open-source software factory: /office-hours writes a design doc, four plan reviews amend it, only then
anything is built).

The lane: officehours action=start opens a per-tenant baithak (data/officehours/<tenant>/officehours.db,
office_docs + office_reviews) and returns the SIX forcing questions; action=doc writes the design doc
(reframe / capabilities / premises / options with effort / recommendation / wedge); action=review appends
one lens row (ceo|design|devex|eng) - eng ALWAYS last and the eng lens is what flips status to reviewed;
action=decide records HER decision in her words; action=stop closes. officehours_dekho reads (list / doc
/ reviews). NOTHING auto-runs off a doc - the wedge is advisory, real work happens later with her Haan.

Everything runs OFFLINE: pure sqlite + config, no network, no browser, no worker.
"""
import asyncio
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

from app.agent import officehours_tools as oh
from app.agent.tools import Ctx, TOOLS, HANDLERS, TOOL_LABELS, FAMILY_OF

CTX = Ctx(tenant_id="oh-test-tenant", conversation_id="c1")
CTX2 = Ctx(tenant_id="oh-other-tenant", conversation_id="c2")


def _run(coro):
    return asyncio.run(coro)


def _wipe(tenant):
    shutil.rmtree(Path("data") / "officehours" / tenant, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_state():
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)
    yield
    for t in (CTX.tenant_id, CTX2.tenant_id):
        _wipe(t)


def _start(topic="naya product idea", **kw):
    return _run(oh.officehours(CTX, action="start", topic=topic, **kw))


def _doc(did, **kw):
    base = dict(reframe="she asked X, she needs Y", capabilities=["a", "b"],
                premises=[{"challenge": "p1", "answer": "ok"}],
                options=[{"name": "wedge", "effort": "day", "what": "small", "why": "alone useful"}],
                recommendation="wedge", wedge="one page form")
    base.update(kw)
    return _run(oh.officehours(CTX, action="doc", officehours_id=did, **base))


# --------------------------------------------------------------------------- registry

def test_registry_531_and_wired():
    names = {t["name"] for t in TOOLS}
    assert len(TOOLS) == 625, "624 + 1 ai_app (v0.785 HOOLA AI APPS). 623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " "581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH: workspace + kgmemory). Was: 541 (v0.502) + 1 magic21 (v0.512) + 1 dhara_dsl (their v0.514) + 10 construction (v0.522) + 1 crew_run (v0.523) + 2 from main's v0.533 CRAWL BRAIN wiring (healed in v0.537: red on pristine main) + 1 reach (v0.559 REACH MANCH) + 1 speckit (v0.569 SPEC SUTRA)"
    assert {"officehours", "officehours_dekho"} <= names
    assert {"officehours", "officehours_dekho"} <= set(HANDLERS)
    assert "officehours" in TOOL_LABELS and "officehours_dekho" in TOOL_LABELS
    assert FAMILY_OF.get("officehours") == "officehours"


def test_story_and_prompts_pins():
    from app import main as main_mod
    from app.agent import prompts
    assert main_mod.APP_VERSION == "0.794.0"
    story = (Path(main_mod.__file__).read_text().split("APP_VERSION = ", 1)[1])[:20000]
    # story pin rides the NEWEST release's story (the v0.476 precedent); the OFFICE HOURS
    # story tokens live in git history (the v0.497 chain moved them here from v0.479)
    assert "HOOLA MIDDLEWARE" in story and "server/app/aep" in story   # the newest-story precedent (the newest story carries the marker)
    ptxt = Path(prompts.__file__).read_text()
    assert "OFFICE HOURS (v0.495" in ptxt and "eng is ALWAYS last" in ptxt
    assert "`officehours` action=start" in ptxt


# --------------------------------------------------------------------------- start (the six questions)

def test_start_creates_draft_with_six_questions():
    out = _start(topic="bill yaad rakhne ka system")
    assert out["status"] == "draft"
    assert out["already_open"] is False
    assert out["officehours_id"].startswith("oh_")
    assert len(out["questions"]) == 6
    assert any("wedge" in q for q in out["questions"])
    assert any("kill" in q.lower() or "bekaar" in q for q in out["questions"])


def test_start_requires_topic():
    with pytest.raises(Exception) as e:
        _run(oh.officehours(CTX, action="start", topic="   "))
    assert "topic" in str(e.value)


def test_start_dedupes_same_open_topic():
    a = _start(topic="GST filing helper")
    b = _start(topic="gst filing helper")
    assert a["officehours_id"] == b["officehours_id"]
    assert a["already_open"] is False and b["already_open"] is True


def test_start_clamps_long_topic():
    out = _start(topic="x" * 500)
    row = oh.get_doc(CTX.tenant_id, out["officehours_id"])
    assert len(row["topic"]) == oh._TOPIC_CAP


def test_start_clamps_her_words_and_pain():
    out = _start(topic="t", her_words="h" * 5000, pain="p" * 5000)
    row = oh.get_doc(CTX.tenant_id, out["officehours_id"])
    assert len(row["her_words"]) == oh._TEXT_CAP and len(row["pain"]) == oh._TEXT_CAP


# --------------------------------------------------------------------------- doc (the design doc)

def test_doc_saves_sections_and_caps():
    out = _start()
    did = out["officehours_id"]
    caps = [{"point": f"c{i}"} for i in range(10)]                 # 10 -> 7
    prems = [{"challenge": f"p{i}" * 100, "answer": "haan"} for i in range(9)]  # 9 -> 7, clamped
    opts = [{"name": f"opt{i}", "effort": "day", "what": "w", "why": "b"} for i in range(6)]  # 6 -> 4
    d = _doc(did, capabilities=caps, premises=prems, options=opts)
    assert d["status"] == "doc"
    row = oh.get_doc(CTX.tenant_id, did)
    assert len(row["capabilities"]) == 7 and len(row["premises"]) == 7 and len(row["options"]) == 4
    assert all(len(p["challenge"]) <= oh._PREM_LEN for p in row["premises"])
    assert row["recommendation"] == "wedge" and row["wedge"] == "one page form"


def test_doc_options_effort_clamped_to_known_words():
    out = _start()
    d = _doc(out["officehours_id"], options=[{"name": "o1", "effort": "fortnight", "what": "w", "why": "b"},
                                             {"name": "o2", "effort": "HOURS", "what": "w", "why": "b"}])
    row = oh.get_doc(CTX.tenant_id, out["officehours_id"])
    assert row["options"][0]["effort"] == "days"      # unknown -> the honest middle
    assert row["options"][1]["effort"] == "hours"     # case-insensitive known word stays


def test_doc_on_missing_id_refused():
    with pytest.raises(Exception) as e:
        _doc("oh_nope")
    assert "was not found" in str(e.value)


def test_doc_on_decided_refused():
    out = _start()
    _doc(out["officehours_id"])
    _run(oh.officehours(CTX, action="decide", officehours_id=out["officehours_id"], decision="nahi karna"))
    with pytest.raises(Exception) as e:
        _doc(out["officehours_id"])
    assert "decided/stopped" in str(e.value)


# --------------------------------------------------------------------------- review (the four lenses, eng last)

def test_review_on_draft_refused():
    out = _start()
    with pytest.raises(Exception) as e:
        _run(oh.officehours(CTX, action="review", officehours_id=out["officehours_id"],
                            lens="ceo", verdict="GO", findings=["f1"]))
    assert "action=doc" in str(e.value)


def test_review_ceo_keeps_status_doc():
    out = _start()
    _doc(out["officehours_id"])
    r = _run(oh.officehours(CTX, action="review", officehours_id=out["officehours_id"],
                            lens="ceo", verdict="SHRINK", findings=["scope bada hai"],
                            changes=["wedge pe ruk jao"]))
    assert r["status"] == "doc"
    assert any(x.startswith("ceo:SHRINK") for x in r["reviews_so_far"])


def test_review_eng_flips_to_reviewed():
    out = _start()
    _doc(out["officehours_id"])
    _run(oh.officehours(CTX, action="review", officehours_id=out["officehours_id"], lens="ceo", verdict="GO"))
    _run(oh.officehours(CTX, action="review", officehours_id=out["officehours_id"], lens="design", verdict="GO"))
    r = _run(oh.officehours(CTX, action="review", officehours_id=out["officehours_id"], lens="eng",
                            verdict="GO", findings=["edge case: empty list"], changes=["test plan jodo"]))
    assert r["status"] == "reviewed"
    assert len(r["reviews_so_far"]) == 3


def test_review_bad_lens_refused():
    out = _start()
    _doc(out["officehours_id"])
    with pytest.raises(Exception) as e:
        _run(oh.officehours(CTX, action="review", officehours_id=out["officehours_id"],
                            lens="garry", verdict="GO"))
    assert "lens" in str(e.value)


def test_review_findings_capped_and_clamped():
    out = _start()
    _doc(out["officehours_id"])
    _run(oh.officehours(CTX, action="review", officehours_id=out["officehours_id"], lens="eng",
                        verdict="GO", findings=[f"f{i}" * 200 for i in range(15)],
                        changes=[f"c{i}" * 200 for i in range(15)]))
    revs = oh.list_reviews(CTX.tenant_id, out["officehours_id"])
    assert len(revs[0]["findings"]) == 12 and len(revs[0]["changes"]) == 12
    assert all(len(f) <= oh._FIND_LEN for f in revs[0]["findings"])


def test_review_after_decided_refused():
    out = _start()
    _doc(out["officehours_id"])
    _run(oh.officehours(CTX, action="decide", officehours_id=out["officehours_id"], decision="karna hai"))
    with pytest.raises(Exception) as e:
        _run(oh.officehours(CTX, action="review", officehours_id=out["officehours_id"], lens="eng", verdict="GO"))
    assert "decided/stopped" in str(e.value)


# --------------------------------------------------------------------------- decide + stop (hers)

def test_decide_records_her_words():
    out = _start()
    _doc(out["officehours_id"])
    d = _run(oh.officehours(CTX, action="decide", officehours_id=out["officehours_id"],
                            decision="wedge pe chalo", next_step="form ka design"))
    assert d["status"] == "decided"
    assert d["decision"] == "wedge pe chalo" and d["next_step"] == "form ka design"


def test_decide_requires_her_words():
    out = _start()
    with pytest.raises(Exception) as e:
        _run(oh.officehours(CTX, action="decide", officehours_id=out["officehours_id"], decision="  "))
    assert "decision" in str(e.value)


def test_decide_twice_refused():
    out = _start()
    _run(oh.officehours(CTX, action="decide", officehours_id=out["officehours_id"], decision="haan"))
    with pytest.raises(Exception) as e:
        _run(oh.officehours(CTX, action="decide", officehours_id=out["officehours_id"], decision="phir se"))
    assert "decided/stopped" in str(e.value)


def test_stop_closes():
    out = _start()
    d = _run(oh.officehours(CTX, action="stop", officehours_id=out["officehours_id"]))
    assert d["status"] == "stopped"
    with pytest.raises(Exception):
        _doc(out["officehours_id"])


# --------------------------------------------------------------------------- dekho (read-only)

def test_dekho_list_latest_first_and_empty_honest():
    empty = _run(oh.officehours_dekho(CTX, what="list"))
    assert empty["total"] == 0 and "action=start" in empty["note"]
    a = _start(topic="pehla")
    b = _start(topic="doosra")
    lst = _run(oh.officehours_dekho(CTX, what="list"))
    assert lst["total"] == 2 and lst["count"] == 2
    assert lst["docs"][0]["officehours_id"] == b["officehours_id"]   # latest first
    assert lst["docs"][1]["officehours_id"] == a["officehours_id"]
    assert set(lst["docs"][0].keys()) >= {"officehours_id", "topic", "status", "wedge"}


def test_dekho_doc_full_sections():
    out = _start(topic="poora doc dekho")
    _doc(out["officehours_id"])
    d = _run(oh.officehours_dekho(CTX, what="doc", officehours_id=out["officehours_id"]))
    assert d["officehours_id"] == out["officehours_id"]
    assert d["reframe"] == "she asked X, she needs Y"
    assert len(d["questions"]) == 6 and d["reviews_count"] == 0
    assert d["options"][0]["name"] == "wedge"


def test_dekho_reviews_rows_newest_first():
    out = _start()
    _doc(out["officehours_id"])
    _run(oh.officehours(CTX, action="review", officehours_id=out["officehours_id"], lens="ceo", verdict="GO"))
    _run(oh.officehours(CTX, action="review", officehours_id=out["officehours_id"], lens="eng", verdict="REWORK"))
    r = _run(oh.officehours_dekho(CTX, what="reviews", officehours_id=out["officehours_id"]))
    assert r["count"] == 2
    assert r["reviews"][0]["lens"] == "eng"          # newest first
    assert r["reviews"][0]["verdict"] == "REWORK"


def test_dekho_defaults_to_latest_and_unknown_what_refused():
    out = _start()
    _doc(out["officehours_id"])
    d = _run(oh.officehours_dekho(CTX, what="doc"))           # no id = latest
    assert d["officehours_id"] == out["officehours_id"]
    with pytest.raises(Exception) as e:
        _run(oh.officehours_dekho(CTX, what="sab kuch"))
    assert "what" in str(e.value)


def test_dekho_actions_without_any_baithak_refused():
    for act, kw in (("doc", {}), ("review", {"lens": "ceo"}), ("decide", {"decision": "x"}), ("stop", {})):
        with pytest.raises(Exception) as e:
            _run(oh.officehours(CTX, action=act, **kw))
        assert "action=start" in str(e.value)


# --------------------------------------------------------------------------- house rules

def test_tenant_isolation():
    out = _start(topic="sirf uska idea")
    other = _run(oh.officehours_dekho(CTX2, what="list"))
    assert other["total"] == 0
    with pytest.raises(Exception) as e:
        _run(oh.officehours_dekho(CTX2, what="doc", officehours_id=out["officehours_id"]))
    assert "was not found" in str(e.value)


def test_disabled_switch(monkeypatch):
    monkeypatch.setattr("app.config.get_settings",
                        lambda: SimpleNamespace(officehours_enabled=False))
    with pytest.raises(Exception) as e:
        _start()
    assert "officehours_enabled=false" in str(e.value)


def test_forget_old_keeps_newest_30(monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(oh.time, "time", lambda: (t.__setitem__(0, t[0] + 1) or t[0]))
    ids = []
    for i in range(31):
        ids.append(oh.start_doc(CTX.tenant_id, f"topic {i}", "", "", keep=30)["id"])
    docs, total = oh.list_docs(CTX.tenant_id, limit=100)
    assert total == 30 and ids[0] not in {d["id"] for d in docs} and ids[-1] in {d["id"] for d in docs}


def test_nothing_autoruns_doc_is_advisory():
    """The doc's wedge/next_step never spawns work: no handler call, no card, no kaam - just stored text."""
    out = _start()
    _doc(out["officehours_id"])
    d = _run(oh.officehours(CTX, action="decide", officehours_id=out["officehours_id"],
                            decision="karna hai", next_step="kal subah form"))
    row = oh.get_doc(CTX.tenant_id, out["officehours_id"])
    assert row["status"] == "decided" and row["next_step"] == "kal subah form"
    assert d["note"] and "yes" in d["note"]      # the honest line: real work waits for her Haan
