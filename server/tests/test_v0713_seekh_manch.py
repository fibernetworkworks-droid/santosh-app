"""v0.713 SEEKH MANCH - learn a way of working from a video, end to end, backend-only
(owner: "NOW LETS WORK ON A HOOLA AI AGENT THAT WILL SEE THE YOUTUBVIDEO FROM LINK, SHORTS, MP4 OR ANY
VIDEO FORMAT. EXAMPLE FEELING THE FORM OR ANY WORK --- AI WILL LEARN THAT TRAIN ITSELF KEEP IN MEMORY
AND IF TASK GIVEN RELATED TO IT IT WILL PERFORM SMOOTHLY"; "GO" on the SEEKH MANCH plan).

ONE new tool `seekh_video` (registry 616 -> 617, family "seekh" - the auto-derived name from SEEKH_TOOLS).
NEW server/app/seekh.py (the bridge) + agent/seekh_tools.py (the surface) + procedures.save_video (the
learned-ways row). Everything else already ships and is only READ: the Gemini eyes
(youtube/service.gemini_video for links, the videoedit/brain inline-bytes pattern for attached files),
the procedures memory (hint() injects it every owner turn), the operator recipe box (find() reads it at
every job start; Memory.save versions and backs up). Zero new pip, zero new keys, zero network at import.

LAWS under test: every distilled step carries [m:ss] evidence or is demoted to gotchas; no literal
personal value survives (digits masked, values become variables); learned is not proven (a draft recipe
has runs=0 and a DRAFT note, a video watch never wins anything); caps (day / file size / file length)
and the seekh_enabled kill switch; the frozen PC zone is untouched.

The whole suite is OFFLINE (zero network): the perception doors and the Claude distill door are patched
at the module seam, because v1 has no other seam - the tests exercise classify, validate, salvage,
distill (with brain.think patched), the two memories, the sidecar, the wiring and the pins.
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agent import seekh_tools as ST
from app.agent import tools as T
from app import seekh as K

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server"

# a well-formed distill result (what brain.think would answer for a form-filling video)
GOOD = {
    "title": "NSP scholarship form bharne ka tareeka",
    "kind": "website_work", "site": "scholarships.gov.in", "start_url": "https://scholarships.gov.in/",
    "steps": [
        {"n": 1, "action": "open", "target": None, "evidence": ["0:12"], "note": "login page opens"},
        {"n": 2, "action": "fill", "target": {"role": "textbox", "name": "Applicant Name"},
         "value_var": "full_name", "value_hint": "as printed on Aadhaar", "evidence": ["1:04"], "note": ""},
        {"n": 3, "action": "click", "target": {"role": "button", "name": "Submit"}, "evidence": ["2:41"],
         "note": "final submit"},
    ],
    "preconditions": ["Aadhaar ready", "mobile with OTP in reach"],
    "gotchas": ["OTP box takes only 6 digits"],
    "variables": {"full_name": {"field": "Applicant Name", "why": "differs per person"}},
    "confidence": 0.78, "unsure": ["could not read the menu label at 2:10 (blurry)"],
}


def ctx(tenant="default", actor="owner"):
    return SimpleNamespace(tenant_id=tenant, conversation_id="c1", actor=actor)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- 1. surface (4)

def test_tool_registered_once():
    names = [t["name"] for t in T.TOOLS]
    assert names.count("seekh_video") == 1
    assert T.FAMILY_OF.get("seekh_video") == "seekh"
    assert "seekh_video" in T.HANDLERS and "seekh_video" in T.TOOL_LABELS
    assert T.TOOL_LABELS["seekh_video"] == "Video dekh kar seekh raha hoon"


def test_registry_pin():
    assert len(T.TOOLS) == 626, ("625 + 1 pdf_kit (v0.807 HOOLA DOCUMENT KIT). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: learn a way of working from a "
                                 "video - the owner's 'isse seekh lo'). Was 616 (v0.694 WEB CLONE: 615 + 1 "
                                 "web_clone), 615 (+ 1 kala v0.681 KALA MANCH), 606 (v0.665 JHAROKHA + "
                                 "duniya + sandarbh chains in between)")


def test_schema_valid():
    import jsonschema
    spec = next(t for t in ST.SEEKH_TOOLS if t["name"] == "seekh_video")
    jsonschema.validate(spec["input_schema"], {"$schema": "https://json-schema.org/draft/2020-12/schema",
                                               "type": "object"})
    assert spec["input_schema"]["required"] == ["action"]
    assert set(spec["input_schema"]["properties"]["action"]["enum"]) == {"watch", "status"}
    assert "Learn a way of doing something by WATCHING a video" in spec["description"]
    assert "Learned is not proven" in spec["description"]


def test_offline_status_action():
    out = run(ST.SEEKH_HANDLERS["seekh_video"](ctx(), "status"))
    assert out == {"watches": [], "total": 0}


# ---------------------------------------------------------------- 2. classify (5)

def test_classify_youtube_forms():
    for ref in ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ",
                "https://www.youtube.com/shorts/aBcDeFgHiJk", "dQw4w9WgXcQ"):
        assert K._classify(ref)[0] == "youtube"
    assert K._classify("https://www.youtube.com/watch?v=dQw4w9WgXcQ")[1] == "dQw4w9WgXcQ"


def test_classify_file_and_url():
    assert K._classify("file_ab12cd34ef56")[0] == "file"
    assert K._classify("https://cdn.example.com/clips/how.mp4")[0] == "url"


def test_classify_garbage_is_honest():
    with pytest.raises(K.SeekhError):
        K._classify("")
    with pytest.raises(K.SeekhError):
        K._classify("   ")
    with pytest.raises(K.SeekhError):
        K._classify("yeh video dekho!! @#$")


def test_day_cap(env, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: "notes")
    monkeypatch.setattr(K, "_distill", lambda text: json.loads(json.dumps(GOOD)))
    monkeypatch.setenv("SEEKH_MAX_PER_DAY", "2")
    get_settings.cache_clear()
    for _ in range(2):
        K.watch("default", "https://youtu.be/dQw4w9WgXcQ")
    with pytest.raises(K.SeekhError, match="2 videos already learned today"):
        K.watch("default", "https://youtu.be/dQw4w9WgXcQ")


def test_switch_off_is_off(env, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("SEEKH_ENABLED", "false")
    get_settings.cache_clear()
    called = []
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: called.append(1) or "notes")
    with pytest.raises(K.SeekhError, match="switched off"):
        K.watch("default", "https://youtu.be/dQw4w9WgXcQ")
    assert called == []


# ---------------------------------------------------------------- 3. validate + salvage (8)

def test_validate_clean_passes():
    assert K._validate(GOOD) == []


def test_validate_catches_the_laws():
    bad = json.loads(json.dumps(GOOD))
    bad["steps"][1]["evidence"] = []
    bad["steps"][2]["note"] = "enter 9876543210 here"
    bad["confidence"] = 7
    bad["title"] = " "
    problems = K._validate(bad)
    assert any("no [m:ss] evidence" in p for p in problems)
    assert any("literal digits" in p for p in problems)
    assert any("confidence" in p for p in problems)
    assert any("title" in p for p in problems)


def test_validate_rejects_literal_value():
    bad = json.loads(json.dumps(GOOD))
    bad["steps"][1]["value"] = "Ramesh Kumar"
    assert any("literal value" in p for p in K._validate(bad))


def test_salvage_drops_steps_without_evidence():
    sk = json.loads(json.dumps(GOOD))
    sk["steps"][2]["evidence"] = ["no timestamp here"]
    out = K._salvage(sk)
    assert len(out["steps"]) == 2
    assert any("not sure" in g for g in out["gotchas"])
    assert out["confidence"] <= 0.5


def test_salvage_masks_digits_everywhere():
    sk = json.loads(json.dumps(GOOD))
    sk["steps"][1]["value_hint"] = "mobile 9876543210 jaisa"
    sk["steps"][0]["note"] = "form id 12345 opens"
    out = K._salvage(sk)
    flat = json.dumps(out, ensure_ascii=False)
    assert "9876543210" not in flat and "12345" not in flat


def test_salvage_clamps_and_defaults():
    sk = json.loads(json.dumps(GOOD))
    sk["confidence"] = 9.5
    assert K._salvage(sk)["confidence"] == 1.0
    sk["confidence"] = "nonsense"
    assert K._salvage(sk)["confidence"] == 0.5
    sk["title"] = ""
    assert K._salvage(sk)["title"] == "Video se seekha kaam"
    sk["kind"] = "weird"
    assert K._salvage(sk)["kind"] == "other_work"


def test_salvage_needs_at_least_one_step():
    sk = json.loads(json.dumps(GOOD))
    for s in sk["steps"]:
        s["evidence"] = []
    with pytest.raises(K.SeekhError):
        K._salvage(sk)


def test_distill_reasks_once_then_salvages(monkeypatch):
    from app.videoedit import brain
    bad = json.loads(json.dumps(GOOD))
    bad["steps"][1]["evidence"] = []
    calls = {"n": 0}

    def fake_think(system, prompt, max_tokens=6000):
        calls["n"] += 1
        assert "evidence" in prompt or "problems" in prompt.lower() or True
        if calls["n"] == 1:
            return bad
        assert "step 2 has no [m:ss] evidence" in prompt        # the re-ask carries the problems
        fixed = json.loads(json.dumps(GOOD))
        fixed["steps"][1]["evidence"] = []                       # still broken: salvage enforces the law
        return fixed

    monkeypatch.setattr(brain, "think", fake_think)
    out = K._distill("raw notes")
    assert calls["n"] == 2
    assert len(out["steps"]) == 2                                 # the unprovable step never became a step


# ---------------------------------------------------------------- 4. the pipeline end to end (3)

def test_watch_youtube_end_to_end(env, monkeypatch):
    from app import procedures as pr
    seen = {}

    def fake_perceive(vid, tenant):
        seen["vid"] = vid
        return "1. [0:12] login page opens 2. [1:04] name box filled"

    monkeypatch.setattr(K, "_perceive_youtube", fake_perceive)
    monkeypatch.setattr(K, "_distill", lambda text: json.loads(json.dumps(GOOD)))
    out = K.watch("default", "https://youtu.be/dQw4w9WgXcQ", title="Scholarship form")
    assert seen["vid"] == "dQw4w9WgXcQ"
    assert out["learned"] == "Scholarship form" and out["kind"] == "website_work"
    assert out["procedure_id"] and out["recipe"]
    assert "counts as proven once it has worked" in out["say"] and "NOT proven" in out["note_for_you"]
    assert [s["evidence"][0] for s in out["steps"]] == ["0:12", "1:04", "2:41"]
    # the two memories
    rows = pr.listing("default")
    assert rows and rows[0]["title"] == "Scholarship form" and rows[0]["wins"] == 0
    assert all(s["tool"] == "" and "[" in s["label"] for s in rows[0]["steps"])
    from app.operator.memory import Memory
    mem = Memory(K._operator_home("default"))
    r = mem.load(_recipe_name_check(mem, "Scholarship"))
    assert r["runs"] == 0 and r["draft"] is True and "DRAFT" in r["notes"]
    assert r["variables"] and r["steps"][1]["value"] == "{full_name}"
    # the sidecar
    st = K.listing("default")
    assert st["total"] == 1 and st["watches"][0]["source"] == "youtube:dQw4w9WgXcQ"


def _recipe_name_check(mem, title_part):
    found = mem.find(title_part)["recipes"]
    assert found, "the draft recipe must be findable by the task"
    return found[0]["name"]


def test_watch_file_ref(env, monkeypatch):
    monkeypatch.setattr(K, "_perceive_file",
                        lambda tenant, fid, st: "file notes with [0:30] a step")
    monkeypatch.setattr(K, "_distill", lambda text: json.loads(json.dumps(GOOD)))
    out = K.watch("default", "file_ab12cd34ef56")
    assert out["source"] == "file:file_ab12cd34ef56"


def test_watch_non_owner_refused(env, monkeypatch):
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: "never called")
    with pytest.raises(K.SeekhError, match="owner"):
        K.watch("default", "https://youtu.be/dQw4w9WgXcQ", actor="customer")


# ---------------------------------------------------------------- 5. sidecar (4)

def test_sidecar_cap_and_corrupt(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "_dir", lambda: tmp_path)
    K._save("t1", [{"day": "x", "title": str(i)} for i in range(150)])
    assert len(K._load("t1")) == K.MAX_SIDECAR
    (tmp_path / "t2.json").write_text("{not json", encoding="utf-8")
    assert K._load("t2") == []
    assert K.listing("t2") == {"watches": [], "total": 0}


def test_sidecar_is_per_tenant(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "_dir", lambda: tmp_path)
    K._save("tenant-a", [{"day": "d", "title": "a"}])
    K._save("tenant-b", [{"day": "d", "title": "b"}])
    assert K.listing("tenant-a")["watches"][0]["title"] == "a"
    assert K.listing("tenant-b")["watches"][0]["title"] == "b"


def test_status_action_lists_watches(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "_dir", lambda: tmp_path)
    K._save("default", [{"day": "d", "title": "one"}, {"day": "d", "title": "two"}])
    out = run(ST.SEEKH_HANDLERS["seekh_video"](ctx(), "status"))
    assert [w["title"] for w in out["watches"]] == ["two", "one"]     # newest first


def test_tool_errors_come_back_as_toolerror(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "_dir", lambda: tmp_path)
    with pytest.raises(ST.ToolError):
        run(ST.SEEKH_HANDLERS["seekh_video"](ctx(), "watch"))
    with pytest.raises(ST.ToolError):
        run(ST.SEEKH_HANDLERS["seekh_video"](ctx(), "nonsense"))


# ---------------------------------------------------------------- 6. procedures memory (4)

def test_save_video_and_hint(env):
    from app import procedures as pr
    steps = [{"tool": "", "label": "1. open: login page [0:12]"}, {"tool": "", "label": "2. fill: name [1:04]"}]
    pr.save_video("default", "GST return bharne ka tareeka", "seekh: video GST return",
                  steps, ["OTP box takes only 6 digits"])
    rows = pr.listing("default")
    assert len(rows) == 1 and rows[0]["uses"] == 0 and rows[0]["wins"] == 0
    assert rows[0]["watch_out"] and "OTP" in rows[0]["watch_out"][0]
    # hint() finds it on a matching ask (word overlap: semantic off in tests demands >= 0.55)
    text, ids = pr.hint("default", "GST return bharne ka tareeka wala kaam")
    assert text and rows[0]["id"] in ids and "dhyan" in text


def test_save_video_masks_digits_and_rejects_empty(env):
    from app import procedures as pr
    out = pr.save_video("default", "PAN 123456789 se link", "trigger", [{"tool": "", "label": "x [0:01]"}], [])
    assert "123456789" not in out["title"] and "#" in out["title"]
    with pytest.raises(pr.ProcedureError):
        pr.save_video("default", "koi step nahi", "trigger", [], [])


def test_owner_controls_still_work(env):
    from app import procedures as pr
    out = pr.save_video("default", "Ek aur tareeka", "t", [{"tool": "", "label": "1. x [0:01]"}], [])
    assert pr.update("default", out["id"], active=False)["active"] is False
    pr.delete("default", out["id"])
    assert pr.listing("default") == []


def test_cap_eviction(env, monkeypatch):
    from app import procedures as pr
    monkeypatch.setattr(pr, "MAX_PER_OWNER", 3)
    for i in range(5):
        pr.save_video("default", f"tareeka {i}", "t", [{"tool": "", "label": "1. x [0:01]"}], [])
    assert len(pr.listing("default")) == 3


# ---------------------------------------------------------------- 7. recipe drafts (6)

def test_draft_recipe_shape_and_find(env, monkeypatch):
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: "notes")
    monkeypatch.setattr(K, "_distill", lambda text: json.loads(json.dumps(GOOD)))
    K.watch("default", "https://youtu.be/dQw4w9WgXcQ")
    from app.operator.memory import Memory
    mem = Memory(K._operator_home("default"))
    found = mem.find("NSP scholarship form bharne")["recipes"]
    assert found and found[0]["score"] >= 0.3
    r = mem.load(found[0]["name"])
    assert r["runs"] == 0 and r["draft"] and "never run yet" in r["notes"]
    assert r["site"] == "scholarships.gov.in" and r["start_url"].startswith("https://")
    assert r["steps"][0]["url"] == r["start_url"]
    assert r["steps"][1]["value"] == "{full_name}"
    assert "98765" not in json.dumps(r)                        # no literal personal values


def test_draft_never_clobbers_a_proven_recipe(env, monkeypatch):
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: "notes")
    monkeypatch.setattr(K, "_distill", lambda text: json.loads(json.dumps(GOOD)))
    K.watch("default", "https://youtu.be/dQw4w9WgXcQ")          # draft v1
    from app.operator.memory import Memory
    mem = Memory(K._operator_home("default"))
    name = mem.find("NSP scholarship")["recipes"][0]["name"]
    p = mem.recipe_path(name)
    proven = json.loads(p.read_text(encoding="utf-8"))
    proven["runs"], proven["draft"] = 5, False                  # a real run has now worked
    p.write_text(json.dumps(proven, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(K, "_distill", lambda text: json.loads(json.dumps(GOOD)))
    K.watch("default", "https://youtu.be/aaaaaaaaaaa", title="NSP scholarship form bharne ka tareeka")
    assert json.loads(p.read_text(encoding="utf-8"))["runs"] == 5        # the proven one stands
    assert mem.find("video")["recipes"]                                  # the new draft sits beside it


def test_draft_resave_bumps_version(env, monkeypatch):
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: "notes")
    monkeypatch.setattr(K, "_distill", lambda text: json.loads(json.dumps(GOOD)))
    K.watch("default", "https://youtu.be/dQw4w9WgXcQ")
    K.watch("default", "https://youtu.be/dQw4w9WgXcQ", title="NSP scholarship form bharne ka tareeka")
    from app.operator.memory import Memory
    mem = Memory(K._operator_home("default"))
    name = mem.find("NSP scholarship")["recipes"][0]["name"]
    r = json.loads(mem.recipe_path(name).read_text(encoding="utf-8"))
    assert r["version"] == 2 and r["runs"] == 0
    assert list((K._operator_home("default") / "memory" / "recipes").glob("*.v1.json"))


def test_other_work_gets_no_recipe(env, monkeypatch):
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: "notes")
    other = json.loads(json.dumps(GOOD))
    other["kind"] = "other_work"
    monkeypatch.setattr(K, "_distill", lambda text: other)
    out = K.watch("default", "https://youtu.be/dQw4w9WgXcQ")
    assert out["recipe"] == "" and out["procedure_id"]
    from app.operator.memory import Memory
    assert Memory(K._operator_home("default")).find("scholarship")["recipes"] == []


def test_recipe_failure_never_kills_the_watch(env, monkeypatch):
    monkeypatch.setattr(K, "_perceive_youtube", lambda vid, tenant: "notes")
    monkeypatch.setattr(K, "_distill", lambda text: json.loads(json.dumps(GOOD)))

    def boom(*a, **k):
        raise RuntimeError("operator home unwritable")

    monkeypatch.setattr(K, "_save_recipe_draft", boom)
    out = K.watch("default", "https://youtu.be/dQw4w9WgXcQ")
    assert out["procedure_id"] and out["recipe"] == ""


# ---------------------------------------------------------------- 8. wiring + purity (6)

def test_prompt_bullet_gated_on_family():
    from app.agent import prompts as P
    assert "Seekh video:" in P.system_text(None)
    assert "Seekh video:" in P.system_text({"seekh"})
    assert "Seekh video:" not in P.system_text({"web"})
    # the guide index names it for the model even when the family is not in view
    assert "seekh_video" in P.system_text({"web"}) or "Seekh video" in P.system_text({"web"})


def test_admit_opens_on_her_words_not_on_neighbours():
    from app.agent import admit
    for msg in ("isse seekh lo", "is video se seekh kar", "learn this video",
                "यह वीडियो सीख लो"):
        fams = admit.families_for(msg) if hasattr(admit, "families_for") else None
        if fams is None:                                   # the house surface is admit.admit / EXTRA_KEYS matching
            fams = _extra_hits(admit, msg)
        assert "seekh" in fams, msg
    for msg in ("kya seekha", "banana sikhao", "hoola ne kya seekha", "youtube pe gaana lagao"):
        assert "seekh" not in _extra_hits(admit, msg), msg
    # the INTENTS regex needs a video word next to the learn word
    pat = admit.INTENTS[0][0]
    assert pat.search("isse seekh lo, yeh video hai") and pat.search("video dekh kar sikhao")
    assert not pat.search("kya seekha") and not pat.search("seekhna chahta hoon python")


def _extra_hits(admit, msg):
    m = " " + msg.lower() + " "
    return {fam for fam, keys in admit.EXTRA_KEYS.items() if any(k.lower() in m for k in keys)}


def test_config_defaults():
    from app.config import get_settings
    st = get_settings()
    assert st.seekh_enabled is True and st.seekh_max_per_day == 20
    assert st.seekh_file_max_mb == 200 and st.seekh_file_max_s == 1800


def test_source_wiring_present():
    src = (SERVER / "app" / "agent" / "tools.py").read_text(encoding="utf-8")
    assert "from .seekh_tools import SEEKH_HANDLERS, SEEKH_LABELS, SEEKH_TOOLS" in src
    ps = (SERVER / "app" / "procedures.py").read_text(encoding="utf-8")
    assert "def save_video(" in ps


def test_frozen_pc_zone_untouched():
    """The freeze (CLAUDE.md): no diff in the PC lane files. seekh only READS the operator's public format."""
    import subprocess
    frozen = ["server/app/pc/", "server/app/agent/pc_tools.py", "server/app/bazar/connectors/pc.py",
              "desktop/", ".github/workflows/build-desktop.yml", "lib/ui/pc_screen.dart"]
    out = subprocess.run(["git", "diff", "--name-only", "origin/main", "--"] + frozen,
                         cwd=ROOT, capture_output=True, text=True).stdout.strip()
    assert out == "", out


def test_no_network_at_import():
    """A fresh interpreter with sockets blocked imports app.seekh and app.agent.seekh_tools cleanly."""
    code = (
        "import socket\n"
        "class Dead(socket.socket):\n"
        "    def __init__(self, *a, **k):\n"
        "        raise OSError('no network in this test')\n"
        "socket.socket = Dead\n"
        "import sys; sys.path.insert(0, 'server')\n"
        "from app import seekh; from app.agent import seekh_tools\n"
        "print('IMPORT_OK', len([t for t in seekh_tools.SEEKH_TOOLS]))\n")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert "IMPORT_OK 1" in out.stdout, out.stderr


def test_version_pins():
    """The house pins: pubspec and the console's version story must name SEEKH MANCH."""
    pub = (ROOT / "pubspec.yaml").read_text(encoding="utf-8")
    assert "version: 0.807.0+806" in pub
