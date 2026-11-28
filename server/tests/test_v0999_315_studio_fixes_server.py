"""v0.999.315 STUDIO FIXES (server side): verified flaws of the Hoola Web Studio fixed.

1. The chat tool never deletes a site, takes it offline, restores a version, serves old addresses as live 301s or marks
   money received - it says where she taps it and changes nothing.
2. Connecting a new domain keeps the old (working) domain serving until the new one is live; a failed connect removes
   nothing.
3. _find: LIKE wildcards escaped, drafts never found by name, exact name first, an ambiguous name asks which one,
   destructive callers never act on "the newest site" from an empty ref.
4. Deleting a website deletes its drafts too (folders, data twins, rows); deleting a draft drops its twin.
5. website_dekho has the same staff wall as website.
6. brand_name reads "Sharma Sweets mithai dukaan ki website" as her name.
7. The 'ready' line has no raw preview path and only real scores.
8. The Studio polling /errors records a build error once per version and never reopens a card she ignored.
9. choose_look refuses while the site is busy and never leaves it in 'building' when the build did not start.
10. The live build stream waits on its own thread pool, not the default executor.
11. Ordinary bad input is a 400, not a 500."""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import session
from tests.test_life import conv_ctx
from tests.test_v0280_direct_domains import IP, _direct, _hosts, _tick
from tests.test_v0808_wapas import _fast_checks, _site
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)
from tests.test_v122_hosting import _ready_site, host_env  # noqa: F401  (fixture)

MAIN = Path(__file__).resolve().parents[1] / "app" / "main.py"


def _exists(sid: str) -> bool:
    from app.site.models import Site
    with session() as s:
        return s.get(Site, sid) is not None


# ---------------------------------------------------------------- 1. her tap only, never the chat tool
def test_tool_never_deletes_takes_down_restores_or_confirms_money(site_env, monkeypatch):
    from app.agent import site_tools as STL
    from app.agent.tools import Ctx
    from app.site import hosting as H
    from app.site import moved as MV
    from app.site import service as S
    from app.site import shop as SH
    from app.site import wapas as WP
    ran: list[str] = []
    monkeypatch.setattr(H, "take_down", lambda *a, **k: ran.append("takedown") or {"say": "x"})
    monkeypatch.setattr(WP, "restore", lambda *a, **k: ran.append("restore") or {"restored": True})
    monkeypatch.setattr(MV, "apply", lambda *a, **k: ran.append("moves") or {"ok": True})
    monkeypatch.setattr(SH, "set_status", lambda *a, **k: ran.append("confirm") or {"number": "O-1", "status_text": "x"})
    v = S.new(T, "mithai dukaan ki website", name="Sharma Sweets")
    ctx = Ctx(tenant_id=T, conversation_id=conv_ctx().conversation_id)
    for action, extra in (("delete", {}), ("takedown", {}), ("restore_version", {"version": 1}),
                          ("moves_ok", {"hash": "abc"}), ("shop_order", {"number": "O-1001", "to": "confirmed"})):
        out = asyncio.run(STL.website(ctx, action, site=v["id"], **extra))
        assert out["done"] is False and out["needs_her_tap"] and "Nothing was changed" in out["say"], (action, out)
        assert "Web Studio" in out["say"] or "Shop" in out["say"]
    assert ran == [] and _exists(v["id"])
    # an order step that is not money still goes through
    asyncio.run(STL.website(ctx, "shop_order", site=v["id"], number="O-1001", to="packed"))
    assert ran == ["confirm"]


# ---------------------------------------------------------------- 2. the old domain keeps serving
def test_old_domain_serves_until_the_new_one_is_live(host_env):
    from app.site import dns as D
    from app.site import hosting as H
    world: dict = {}
    _direct(host_env, world)
    host_env["monkeypatch"].setattr(H, "_fetch_ok", lambda host: True)
    g, _ = _ready_site()
    H.connect_domain(T, g["id"], "mithaighar.in")
    lc = H.launch_request(T, g["id"])
    H.launch(T, g["id"], lc["hash"])
    for n in ("mithaighar.in", "www.mithaighar.in"):
        world[(n, "A")] = [IP]
    world[("_hoola.mithaighar.in", "TXT")] = [H.verify_token(T, "mithaighar.in")]
    _tick()
    _tick()
    assert _hosts(g["id"])["mithaighar.in"][0] == "active"
    # a failing connect touches nothing
    mp = host_env["monkeypatch"]
    real_plan = D.make_plan
    mp.setattr(D, "make_plan", lambda *a, **k: (_ for _ in ()).throw(D.DnsError("no plan today")))
    with pytest.raises(H.HostError):
        H.connect_domain(T, g["id"], "newsweets.in")
    h = _hosts(g["id"])
    assert h["mithaighar.in"][0] == "active" and "newsweets.in" not in h
    mp.setattr(D, "make_plan", real_plan)
    # the new domain is pending: the old one still serves
    H.connect_domain(T, g["id"], "newsweets.in")
    h = _hosts(g["id"])
    assert h["mithaighar.in"][0] == "active" and h["newsweets.in"][0] == "pending", h
    # the new one goes live: only now the old one leaves
    lc = H.launch_request(T, g["id"])
    H.launch(T, g["id"], lc["hash"])
    for n in ("newsweets.in", "www.newsweets.in"):
        world[(n, "A")] = [IP]
    world[("_hoola.newsweets.in", "TXT")] = [H.verify_token(T, "newsweets.in")]
    _tick()
    _tick()
    h = _hosts(g["id"])
    assert h["newsweets.in"][0] == "active" and "mithaighar.in" not in h and "www.mithaighar.in" not in h, h


# ---------------------------------------------------------------- 3. finding a site by her words
def test_find_exact_first_ambiguous_asks_wildcards_and_drafts(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.site import drafts as DF
    from app.site import service as S
    sid = _site(S)                                             # "Sharma Sweets", built
    other = S.new(T, "mithai dukaan ki website", name="Sharma Sweets Akola")["id"]   # newer, contains the name
    with session() as s:
        assert S._find(s, T, "sharma sweets").id == sid       # the exact name wins over a newer partial match
        with pytest.raises(S.SiteError, match="More than one website"):
            S._find(s, T, "Sharma")
        with pytest.raises(S.SiteError, match="not found"):
            S._find(s, T, "%")                                  # a wildcard is a letter, not "any website"
        with pytest.raises(S.SiteError, match="not found"):
            S._find(s, T, "_")
        assert S._find(s, T, "Akola").id == other
    d = DF.create(T, sid, "Try")
    S._save(d["id"], name="Sharma Sweets")                     # a draft copies the exact name and is the newest row
    with session() as s:
        assert S._find(s, T, "Sharma Sweets").id == sid
        assert S._find(s, T, d["id"]).id == d["id"]            # by its own id it is still found
        assert S._find(s, T, "").id != d["id"]                  # the "newest" read never lands on a draft
        with pytest.raises(S.SiteError, match="Which website"):
            S._find(s, T, "", newest=False)
    with pytest.raises(S.SiteError, match="Which website"):
        S.delete(T, "")                                         # never "the newest site" for a delete
    assert _exists(sid) and _exists(other)


# ---------------------------------------------------------------- 4. drafts go with their website
def test_delete_removes_drafts_and_their_twins(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.site import build as B
    from app.site import drafts as DF
    from app.site import service as S
    from app.site import twin as TW
    dropped: list[str] = []
    monkeypatch.setattr(DF, "_data_twin", lambda d: f"tw-{d.id}")
    monkeypatch.setattr(TW, "drop", lambda pid: dropped.append(pid))
    sid = _site(S)
    a, b = DF.create(T, sid, "A")["id"], DF.create(T, sid, "B")["id"]
    folder_a = B.site_dir(T, a)                                 # (site_dir makes the folder, so read the path once)
    assert (folder_a / "src").exists() or any(folder_a.iterdir())
    S.delete(T, b)                                              # a draft deleted on its own: its twin goes too
    assert not _exists(b) and dropped == [f"tw-{b}"] and _exists(sid)
    S.delete(T, sid)
    assert not _exists(sid) and not _exists(a) and f"tw-{a}" in dropped
    assert not folder_a.exists()


# ---------------------------------------------------------------- 5. staff read only their own sites
def test_website_dekho_has_the_staff_wall(site_env):
    from app.agent import site_tools as STL
    from app.agent.tools import Ctx, ToolError
    from app.site import care as SC
    from app.site import service as S
    mine = S.new(T, "mithai dukaan ki website", name="Sharma Sweets")["id"]
    theirs = S.new(T, "bakery ki website", name="Kale Bakery")["id"]
    SC.assign(T, mine, staff="ravi")
    staff = Ctx(tenant_id=T, conversation_id=conv_ctx().conversation_id, actor="staff:ravi")
    with pytest.raises(ToolError):
        asyncio.run(STL.website_dekho(staff, "leads", site=""))            # all of the owner's leads: refused
    with pytest.raises(ToolError):
        asyncio.run(STL.website_dekho(staff, "site", site=theirs))
    with pytest.raises(ToolError):
        asyncio.run(STL.website_dekho(staff, "clients"))
    assert asyncio.run(STL.website_dekho(staff, "site", site=mine))["id"] == mine
    assert [x["id"] for x in asyncio.run(STL.website_dekho(staff, "sites"))["sites"]] == [mine]
    owner = Ctx(tenant_id=T, conversation_id=staff.conversation_id)
    assert len(asyncio.run(STL.website_dekho(owner, "sites"))["sites"]) == 2


# ---------------------------------------------------------------- 6. her name in her words
def test_brand_name_reads_her_name(monkeypatch):
    from app.site import ai as AI
    from app.site import service as S
    monkeypatch.setattr(AI, "ask_json", lambda *a, **k: {"name": "Mithaas Ghar", "from_her_words": False})
    got = S.brand_name("Sharma Sweets mithai dukaan ki website, online order WhatsApp par")
    assert got == {"name": "Sharma Sweets", "tagline": "", "by": "her"}
    assert S.brand_name("Kale Dental Clinic: booking chahiye")["name"] == "Kale Dental Clinic"
    assert S.brand_name("Riya ki website")["name"] == "Riya"
    for brief in ("Make a website for my bakery", "Online store for shoes", "I Want A Website"):
        assert S.brand_name(brief, "Bakery")["by"] == "hoola", brief


# ---------------------------------------------------------------- 7. the ready line
def test_ready_line_has_no_path_and_only_real_scores():
    from app.site import service as S
    line = S._say({"status": "ready", "version": 1, "scores": {}, "preview": "/api/site-preview/abc/"})
    assert line == "Website v1 is ready."
    line = S._say({"status": "ready", "version": 2, "scores": {"performance": 91, "seo": 100},
                   "preview": "/api/site-preview/abc/"})
    assert line == "Website v2 is ready. Scores: Speed 91, SEO 100." and "/api/" not in line
    assert S._say({"status": "building", "board": {}}) == "Building the website (0%)."
    assert S._say({"status": "failed", "error": ""}) == "The website build hit a problem."


# ---------------------------------------------------------------- 8. polling the errors
def test_build_error_recorded_once_and_ignored_stays_ignored(site_env):
    from app.main import app
    from app.site import service as S
    sid = S.new(T, "mithai dukaan ki website", name="Sharma Sweets")["id"]
    S._save(sid, status="failed", error="The build stopped at section 3")
    c = TestClient(app)
    for _ in range(3):
        r = c.get(f"/api/sites/{sid}/errors")
        assert r.status_code == 200
    errs = r.json()["errors"]
    assert len(errs) == 1 and errs[0]["count"] == 1, errs
    from app.site import galti as G
    G.set_state(T, sid, errs[0]["id"], "ignored")
    for _ in range(2):
        assert c.get(f"/api/sites/{sid}/errors").json()["errors"] == []
    allv = c.get(f"/api/sites/{sid}/errors?all=1").json()["errors"]
    assert allv[0]["state"] == "ignored" and allv[0]["count"] == 1


# ---------------------------------------------------------------- 9. picking a look while busy
def test_choose_look_refuses_while_busy_and_never_sticks_in_building(site_env, monkeypatch):
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    assert S.get(T, v["id"])["status"] == "looks"
    monkeypatch.setattr(S, "busy", lambda sid: True)
    with pytest.raises(S.SiteError, match="still working"):
        S.choose_look(T, v["id"], 0)
    assert S.get(T, v["id"])["status"] == "looks"
    monkeypatch.setattr(S, "busy", lambda sid: False)
    monkeypatch.setattr(S, "_start", lambda *a, **k: False)    # another job took the site in between
    with pytest.raises(S.SiteError, match="still working"):
        S.choose_look(T, v["id"], 0)
    assert S.get(T, v["id"])["status"] == "looks"


# ---------------------------------------------------------------- 10. the live stream's own threads
def test_live_stream_waits_on_its_own_pool(monkeypatch):
    from app.site import stream as ST
    names: list[str] = []
    monkeypatch.setattr(ST, "wait", lambda sid, since, timeout=15.0: names.append(threading.current_thread().name)
                        or {"seq": 0, "slots": [], "looks": []})

    async def no_default(*a, **k):
        raise AssertionError("the live stream must not use the default executor")
    monkeypatch.setattr(asyncio, "to_thread", no_default)
    out = asyncio.run(ST.wait_async("site-x", 0, 0.01))
    assert out["seq"] == 0 and names and names[0].startswith("site-live")
    src = MAIN.read_text()
    assert "to_thread(ST.wait," not in src and "ST.wait_async(sid, seq, 15.0)" in src


# ---------------------------------------------------------------- 11. bad input is a 400
def test_bad_input_is_a_400_not_a_500(site_env, monkeypatch):
    _fast_checks(monkeypatch)
    from app.main import app
    from app.site import service as S
    sid = _site(S)
    c = TestClient(app, raise_server_exceptions=False)
    for path, body in ((f"/api/sites/{sid}/prototype/edit", {"page": "home", "index": "abc"}),
                       (f"/api/sites/{sid}/prototype/move", {"page": "home", "index": [1], "op": "up"}),
                       (f"/api/sites/{sid}/markup", {"page": "/", "width": "wide"}),
                       (f"/api/sites/{sid}/rollback-request", {"version": [2]}),
                       (f"/api/sites/{sid}/rollback", {"version": {"v": 1}, "hash": "x"})):
        r = c.post(path, json=body)
        assert r.status_code == 400, (path, r.status_code, r.text)
    r = c.post(f"/api/sites/{sid}/preview-errors", json={"items": {"kind": "page"}})
    assert r.status_code == 200, r.text
    r = c.post(f"/api/sites/{sid}/preview-errors", json=[{"kind": ["page"], "m": "x is undefined"}])
    assert r.status_code == 200 and r.json()["recorded"] == 1, r.text
    key = next(iter(S._sections(S._load(sid))))
    r = c.post(f"/api/sites/{sid}/edit", json={"k": key, "e": "1", "op": "style", "value": "[\"color\", \"x\"]"})
    assert r.status_code == 400, r.text
