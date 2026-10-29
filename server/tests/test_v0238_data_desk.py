"""v0.238 DATA DESK (owner: "top 100 AI repos -> PDF" failed; "GO for 1-3 (server only)").

Root cause: every tool result reaching the model is cut to 6,000 characters, so a GitHub search reply showed ~2 repos;
Hoola then escaped to its cloud PC (the hoola_pc_do text called it the place for "heavy/clean work"), the chat stuck
there for 45 min renewed by every result, the goal spun rounds saying "still running", and the cloud PC's file never
came back. Fixes: (1) data_fetch / data_read / data_note keep big data in a server file, the model sees a summary;
doc_studio builds from it (data=) and in parts (part=add); (2) hoola_pc_do = desktop software only; (3) the cloud PC
sticks only when SHE asked, 20 min from the start, never renewed, and data jobs never stick; the goal waits on a
running job instead of spinning.
"""
import asyncio
import json
import time
from datetime import timedelta

import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import gz  # noqa: F401


class _Ctx:
    tenant_id, conversation_id, user_id = "t1", "c1", "u1"


def _repos(n, start=0):
    return [{"full_name": f"org/repo{i}", "stargazers_count": 10000 - i, "description": "x" * 900,
             "owner": {"login": f"org{i}", "id": i}, "topics": ["ai", "llm"], "html_url": f"https://github.com/org/repo{i}",
             "license": {"spdx_id": "MIT"}} for i in range(start, start + n)]


@pytest.fixture
def ds_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATASETS_DIR", str(tmp_path / "ds"))
    return tmp_path / "ds"


# ---------------------------------------------------------------- shaping
def test_find_items_and_pick():
    from app import datasets as D
    reply = {"total_count": 3, "items": _repos(3)}
    assert len(D.find_items(reply)) == 3
    assert len(D.find_items({"data": {"children": [{"a": 1}, {"a": 2}]}})) == 2
    assert D.find_items([{"a": 1}]) == [{"a": 1}]
    with pytest.raises(D.DataError):
        D.find_items(reply, "nope")
    rows = D.pick(D.find_items(reply), ["name=full_name", "stars=stargazers_count", "owner.login", "license.spdx_id",
                                        "topics", "description"])
    assert rows[0] == {"name": "org/repo0", "stars": 10000, "owner_login": "org0", "license_spdx_id": "MIT",
                       "topics": ["ai", "llm"], "description": "x" * D.MAX_CELL + "…"}
    plain = D.pick([{"a": 1, "b": {"c": 2}, "html_url": "u", "d": "z"}])
    assert plain == [{"a": 1, "d": "z"}]                 # nested values and *_url links left out


def test_save_load_slice_annotate_csv(ds_dir):
    from app import datasets as D
    rows = D.pick(_repos(30), ["name=full_name", "stars=stargazers_count"])
    doc = D.save("t1", rows, "AI repos", "https://api.github.com/search/repositories")
    assert doc["count"] == 30 and doc["columns"] == ["name", "stars"] and doc["id"].startswith("ds_")
    again = D.load("t1", doc["id"])
    assert again["rows"][0]["name"] == "org/repo0"
    with pytest.raises(D.DataError):
        D.load("t1", "../etc/passwd")
    with pytest.raises(D.DataError):
        D.load("other-tenant", doc["id"])                # each tenant has its own folder
    part, total = D.rows_slice(again, 0, 5, sort="stars", desc=False)
    assert total == 30 and [r["stars"] for r in part] == [9971, 9972, 9973, 9974, 9975]
    part, total = D.rows_slice(again, 0, 500, q="repo1")
    assert total == 11 and len(part) == 11                # repo1, repo10..repo19
    res = D.annotate("t1", doc["id"], {"org/repo0": "Sabse bada repo", "ORG/REPO1": "Doosra", "nahi-hai": "x"})
    assert res["written"] == 2 and res["not_matched"] == ["nahi-hai"] and res["rows_without_note"] == 28
    assert res["next_to_write"][0] == "org/repo2"
    assert D.load("t1", doc["id"])["rows"][1]["note"] == "Doosra"
    csv = D.to_csv(D.load("t1", doc["id"])).decode("utf-8-sig")
    assert csv.splitlines()[0] == "name,stars,note" and "Sabse bada repo" in csv
    with pytest.raises(D.DataError):
        D.save("t1", [])


# ---------------------------------------------------------------- tools
def test_data_fetch_saves_100_repos_and_shows_only_a_summary(ds_dir, monkeypatch):
    from app.agent import data_tools as dt
    from app.publicapis import service as P
    calls = []

    async def fake_call(tenant, url, params=None, api_id="", headers=None, full=False):
        calls.append(dict(params or {}))
        assert full is True
        page = int((params or {}).get("page", 1))
        items = _repos(50, (page - 1) * 50) if page <= 2 else []
        data = {"total_count": 100, "items": items}
        return {"status": 200, "json": json.dumps(data)[:6000], "_data": data}
    monkeypatch.setattr(P, "call", fake_call)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(dt.asyncio, "sleep", lambda s: real_sleep(0))
    out = asyncio.run(dt.data_fetch(_Ctx(), "https://api.github.com/search/repositories",
                                    {"q": "topic:llm", "sort": "stars", "per_page": 50}, ["name=full_name",
                                    "stars=stargazers_count", "url=html_url", "description"], "items", pages=3))
    assert out["count"] == 100 and out["columns"] == ["name", "stars", "url", "description"]
    assert [c.get("page") for c in calls] == [1, 2, 3]
    assert len(json.dumps(out)) < 4000                   # the model sees a summary, never 100 raw repos
    assert "org/repo0" in out["first_rows"] and "org/repo99" not in out["first_rows"]
    ds = out["dataset"]
    got = asyncio.run(dt.data_read(_Ctx(), ds, offset=90, limit=25))
    assert got["total"] == 100 and "org/repo99" in got["rows"] and got["next_offset"] is None
    got = asyncio.run(dt.data_read(_Ctx(), ds, offset=0, limit=10, fields=["name"]))
    assert got["next_offset"] == 10 and "stars" not in got["rows"]
    lst = asyncio.run(dt.data_read(_Ctx()))
    assert lst["datasets"][0]["dataset"] == ds and lst["datasets"][0]["count"] == 100
    note = asyncio.run(dt.data_note(_Ctx(), ds, {"org/repo0": "LLM framework"}))
    assert note["written"] == 1 and note["rows_without_note"] == 99


def test_data_fetch_stops_on_a_short_page_and_reports_errors(ds_dir, monkeypatch):
    from app.agent import data_tools as dt
    from app.agent.tools import ToolError
    from app.publicapis import service as P
    calls = []

    async def short(tenant, url, params=None, api_id="", headers=None, full=False):
        calls.append(1)
        return {"status": 200, "_data": {"items": _repos(7)}}
    monkeypatch.setattr(P, "call", short)
    out = asyncio.run(dt.data_fetch(_Ctx(), "https://x.example/api", {"per_page": 30}, pages=5))
    assert out["count"] == 7 and len(calls) == 1          # a short first page = nothing more to fetch

    async def bad(tenant, url, params=None, api_id="", headers=None, full=False):
        return {"status": 403, "json": "rate limit"}
    monkeypatch.setattr(P, "call", bad)
    with pytest.raises(ToolError) as e:
        asyncio.run(dt.data_fetch(_Ctx(), "https://x.example/api"))
    assert "403" in str(e.value)

    async def html(tenant, url, params=None, api_id="", headers=None, full=False):
        return {"status": 200, "text": "<html>"}
    monkeypatch.setattr(P, "call", html)
    with pytest.raises(ToolError) as e:
        asyncio.run(dt.data_fetch(_Ctx(), "https://x.example/page"))
    assert "JSON" in str(e.value)


def test_publicapis_full_keeps_the_whole_reply(monkeypatch):
    import inspect
    from app.publicapis import service as P
    assert "full" in inspect.signature(P.call).parameters
    src = inspect.getsource(P.call)
    assert 'out["_data"]' in src


def test_tools_registered_in_the_core_family():
    from app.agent import admit, tools as reg
    names = {t["name"] for t in reg.TOOLS}
    assert {"data_fetch", "data_read", "data_note"} <= names
    for n in ("data_fetch", "data_read", "data_note"):
        assert reg.HANDLERS[n] and reg.TOOL_LABELS[n]
        assert reg.FAMILY_OF[n] == "data"
    assert "data" in admit.CORE_FAMILIES


# ---------------------------------------------------------------- doc_studio from data, in parts
def test_doc_studio_builds_a_pdf_and_xlsx_from_a_dataset_and_parts(ds_dir, monkeypatch):
    from app import datasets as D
    from app.agent import docstudio_tools as dt
    seen = []
    monkeypatch.setattr(dt, "_deliver", lambda ctx, name, data, source: seen.append((name, data)) or
                        {"file_id": "f" + str(len(seen)), "name": name})
    monkeypatch.setattr("app.events.bus.publish", lambda *a, **k: None)
    doc = D.save("t1", D.pick(_repos(100), ["name=full_name", "stars=stargazers_count", "description"]),
                 "AI repos", "https://api.github.com/search/repositories")
    for i in range(0, 100, 25):
        D.annotate("t1", doc["id"], {f"org/repo{j}": f"Repo {j} ka kaam: AI agents." for j in range(i, i + 25)})
    md = dt.data_markdown(D.load("t1", doc["id"]), heading="Top 100")
    assert md.startswith("# Top 100") and "| 100 | org/repo99 |" in md and "### 100. org/repo99" in md
    assert "Repo 99 ka kaam" in md and "> Data: https://api.github.com" in md

    part = asyncio.run(dt.doc_studio(_Ctx(), "pdf", "AI Repos Report", "# Intro\nYeh report 100 repos ki hai.",
                                     part="add"))
    assert part["part"] == "saved" and part["draft_chars"] > 10
    out = asyncio.run(dt.doc_studio(_Ctx(), "pdf", "AI Repos Report", "# Repos\n[[data]]\n\n# Ant mein\nBas.",
                                    data=doc["id"], data_layout="cards"))
    assert out["made"] == "pdf" and seen[-1][1][:5] == b"%PDF-"
    assert not dt._draft_path(_Ctx(), "AI Repos Report").exists()      # the parts are now in the file
    out = asyncio.run(dt.doc_studio(_Ctx(), "xlsx", "AI Repos", data=doc["id"], data_heading="Repos"))
    assert out["made"] == "xlsx" and seen[-1][0].endswith(".xlsx")
    from app.agent.tools import ToolError
    with pytest.raises(ToolError):
        asyncio.run(dt.doc_studio(_Ctx(), "pdf", "X", "y", data="ds_0000000000"))


# ---------------------------------------------------------------- (2) cloud PC wording
def test_hoola_pc_do_is_for_desktop_software_only():
    from app.agent import tools as reg
    d = next(t for t in reg.TOOLS if t["name"] == "hoola_pc_do")["description"]    # what the model sees (dieted)
    assert "heavy/clean work" not in d
    assert "ONLY when the job needs desktop software" in d and "data_fetch" in d
    assert "does NOT come back to the chat" in d


def test_prompt_pins_the_data_desk():
    from app.agent import prompts
    assert "- DATA DESK" in prompts.PINNED
    slim = prompts.system_text(["core"])                  # pinned: rides in every slim turn guide
    assert "- DATA DESK (v0.238" in slim and "api.github.com/search/repositories" in slim


# ---------------------------------------------------------------- (3) stickiness
def test_data_jobs_never_stick_and_the_cloud_pc_sticks_only_when_she_asked():
    from app.agent import where
    where.forget()
    where.worked("c1", "pc_do", {"task": "Open https://github.com and collect the top 100 repos data"})
    assert where.working("c1") == ""                     # a data job never locks a place
    where.worked("c1", "pc_do", {"task": "Open irctc.co.in and fill the booking form"})
    assert where.working("c1") == "pc"                   # a real website form job on her PC still does
    where.forget()
    where.worked("c2", "hoola_pc_do", {"task": "Open https://example.com and fill the form"})
    assert where.working("c2") == ""                     # Hoola's own choice of the cloud PC never sticks
    where.remember("c2", "apne PC par yeh website form bhar do")
    where.worked("c2", "hoola_pc_do", {"task": "Open https://example.com and fill the form"})
    assert where.working("c2") == "hoolapc"
    where.forget()


def test_cloud_pc_lock_is_never_renewed_but_her_pc_still_is():
    from app.agent import where
    where.forget()
    where._PLACE["c3"] = ("hoolapc", time.time())
    where._WORK["c3"] = ("hoolapc", time.time() - where.HOOLAPC_KEEP_S + 5)
    where.touch("c3", "hoolapc")                          # a result note of the running job
    assert where._WORK["c3"][1] < time.time() - where.HOOLAPC_KEEP_S + 10
    where._WORK["c3"] = ("hoolapc", time.time() - where.HOOLAPC_KEEP_S - 1)
    assert where.working("c3") == ""                     # 20 min from the start, then free
    where._WORK["c4"] = ("pc", time.time() - where.HOOLAPC_KEEP_S - 1)
    assert where.working("c4") == "pc"                   # her PC keeps the 45-min rule (v0.104)
    where.touch("c4", "pc")
    assert time.time() - where._WORK["c4"][1] < 2
    where.forget()


# ---------------------------------------------------------------- goal waits on a running job
def _job(conv, minutes_ago=0, state="working"):
    from app.db import now, session
    from app.kaamwatch import KaamJob
    with session() as s:
        s.add(KaamJob(tenant_id="default", conversation_id=conv, key=f"hoolapc:{minutes_ago}", kind="hoolapc",
                      label="Cloud PC", title="Repos", state=state, moved_at=now() - timedelta(minutes=minutes_ago),
                      updated_at=now() - timedelta(minutes=minutes_ago)))


def test_goal_waits_on_a_running_job_instead_of_spinning(gz, monkeypatch):  # noqa: F811
    from app.agent import goal, santosh
    conv = gz["conv"]
    scheduled = []
    monkeypatch.setattr(santosh, "_bg", lambda coro: (scheduled.append(1), coro.close()))
    monkeypatch.setattr(goal, "_waiting_on_her", lambda c: False)
    goal._PENDING.clear()
    v = goal.set_goal("default", conv, "100 repos ki PDF", ["fetch", "write", "pdf"], origin="owner")
    _job(conv)
    assert goal._waiting_on_job(conv) is True
    n0 = goal.STATS["waited_job"]
    assert goal.maybe_continue(conv, "default", "owner") is False and not scheduled
    assert goal.STATS["waited_job"] == n0 + 1
    from app.db import session
    with session() as s:
        assert s.get(goal.GoalRun, v["id"]).paused_at is not None
    assert goal.resume_tick() == 0 and not scheduled     # still running: the sweep keeps waiting


def test_a_dead_or_finished_job_no_longer_holds_the_goal(gz):  # noqa: F811
    from app.agent import goal
    conv = gz["conv"]
    _job(conv, minutes_ago=goal.JOB_WAIT_S // 60 + 5)
    assert goal._waiting_on_job(conv) is False           # not moved for an hour: may be dead
    _job(conv + "x", state="done")
    assert goal._waiting_on_job(conv + "x") is False
    assert goal._waiting_on_job("no-such-chat") is False


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.257.0"
