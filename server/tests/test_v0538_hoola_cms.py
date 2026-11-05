"""v0.538 HOOLA CMS (web Step 6 part 2, W8 "a CMS for her team: editors with roles, drafts, review, scheduled publish,
version history for every page and post").

Invite = one-time link (hash only kept), own password, own login (not her Hoola login), removal ends every login now;
writer -> editor (never their own) -> publisher; a post (new or an edit of a live one) and a PAGE's words / links (only
the elements her Edit mode can change); a text changed meanwhile is never silently overwritten; scheduled drafts go out
at their time; every publish / restore is a revision with what was there before, and a restore is itself a revision."""
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from tests.test_v0538_bada_catalogue import _site
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def _h(tok):
    return {"Authorization": "Bearer " + tok}


def _team(c, sid):
    """Her three invites accepted through the real routes: writer, editor, publisher (+ a second editor)."""
    toks = {}
    for email, role in (("wri@x.in", "writer"), ("edi@x.in", "editor"), ("ed2@x.in", "editor"), ("pub@x.in", "publisher")):
        r = c.post(f"/api/sites/{sid}/cms/invite", json={"email": email, "name": email.split("@")[0], "role": role}).json()
        inv = r["link"].split("invite=")[1]
        assert f"/cms/{sid}/?invite=" in r["link"]
        toks[role if role not in toks else "editor2"] = c.post(f"/api/site-cms/{sid}/accept",
                                                               json={"invite": inv, "password": "long-password-1"}).json()["token"]
        assert c.post(f"/api/site-cms/{sid}/accept", json={"invite": inv, "password": "long-password-1"}).status_code == 403   # once
    return toks


def test_invite_login_roles_and_removal(site_env):
    from app.db import session
    from app.main import app
    from app.site import cms as CM
    from app.site import service as S
    c = TestClient(app)
    sid = _site(S, shop=False)
    toks = _team(c, sid)
    with session() as s:
        assert all(len(m.invite_h) in (0, 64) and m.pw.startswith("pbkdf2$") for m in s.query(CM.SiteCmsMember).all())
    assert c.get(f"/api/site-cms/{sid}/home").status_code == 401
    home = c.get(f"/api/site-cms/{sid}/home", headers=_h(toks["writer"])).json()
    assert home["me"]["role"] == "writer" and any(p["slug"] == "home" for p in home["pages"])
    assert c.post(f"/api/site-cms/{sid}/login", json={"email": "wri@x.in", "password": "nope"}).status_code == 401
    assert c.post(f"/api/site-cms/{sid}/login", json={"email": "wri@x.in", "password": "long-password-1"}).json()["me"]["role"] == "writer"
    assert c.post(f"/api/site-cms/{sid}/accept", json={"invite": "made-up", "password": "long-password-1"}).status_code == 403
    # a token for one site never opens another
    other = _site(S, shop=False)
    assert c.get(f"/api/site-cms/{other}/home", headers=_h(toks["writer"])).status_code == 401
    # her removal ends their login at once; a role change asks them to log in again
    team = c.get(f"/api/sites/{sid}/cms").json()["team"]
    wid = next(m["id"] for m in team if m["email"] == "wri@x.in")
    c.post(f"/api/sites/{sid}/cms/team/{wid}", json={"remove": True})
    assert c.get(f"/api/site-cms/{sid}/home", headers=_h(toks["writer"])).status_code == 401
    assert c.post(f"/api/site-cms/{sid}/login", json={"email": "wri@x.in", "password": "long-password-1"}).status_code == 401
    eid = next(m["id"] for m in team if m["email"] == "edi@x.in")
    c.post(f"/api/sites/{sid}/cms/team/{eid}", json={"role": "publisher"})
    assert c.get(f"/api/site-cms/{sid}/home", headers=_h(toks["editor"])).status_code == 401
    page = c.get(f"/cms/{sid}/")
    assert page.status_code == 200 and "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert page.headers["referrer-policy"] == "no-referrer" and f"'{sid}'" in page.text and "__SITE__" not in page.text


def test_post_review_publish_edit_and_restore(site_env):
    from app.main import app
    from app.site import blog as BL
    from app.site import service as S
    c = TestClient(app)
    sid = _site(S, shop=False)
    toks = _team(c, sid)
    w, e1, e2, p = (_h(toks[k]) for k in ("writer", "editor", "editor2", "publisher"))
    d = c.post(f"/api/site-cms/{sid}/drafts", json={"kind": "post", "title": "Diwali ki mithai",
                                                    "body": "## Kaju katli\n\nIs Diwali hamari kaju katli taaza bani hai.",
                                                    "meta": {"excerpt": "Diwali special", "category": "Festivals"}}, headers=w).json()
    did = d["id"]
    mv = lambda h, to, **kw: c.post(f"/api/site-cms/{sid}/drafts/{did}/move", json={"to": to, **kw}, headers=h)  # noqa: E731
    assert mv(w, "approved").status_code == 403                          # a writer never approves
    assert mv(p, "published").status_code == 409                         # not approved yet
    assert mv(w, "review").status_code == 200
    assert mv(e1, "returned", note="Price bhi likhiye").json()["status"] == "returned"
    c.put(f"/api/site-cms/{sid}/drafts/{did}", json={"body": "## Kaju katli\n\nIs Diwali kaju katli Rs 900 kilo."}, headers=w)
    mv(w, "review")
    assert mv(e1, "approved").json()["reviewer"] == "edi"
    out = mv(p, "published").json()
    assert out["status"] == "published"
    post = next(x for x in BL.posts(sid) if x["title"] == "Diwali ki mithai")
    assert post["status"] == "published" and "Rs 900" in BL.posts(sid)[0].get("body", "") + json.dumps(BL.posts(sid))
    # an editor's OWN draft needs another editor; an edit of the live post becomes a revision with the old text
    d2 = c.post(f"/api/site-cms/{sid}/drafts", json={"kind": "post", "target": post["slug"], "title": "Diwali ki mithai 2026",
                                                     "body": "Ab 950 rupaye kilo."}, headers=e1).json()
    c.post(f"/api/site-cms/{sid}/drafts/{d2['id']}/move", json={"to": "review"}, headers=e1)
    assert c.post(f"/api/site-cms/{sid}/drafts/{d2['id']}/move", json={"to": "approved"}, headers=e1).status_code == 403
    c.post(f"/api/site-cms/{sid}/drafts/{d2['id']}/move", json={"to": "approved"}, headers=e2)
    c.post(f"/api/site-cms/{sid}/drafts/{d2['id']}/move", json={"to": "published"}, headers=p)
    assert next(x for x in BL.posts(sid) if x["slug"] == post["slug"])["title"] == "Diwali ki mithai 2026"
    hist = c.get(f"/api/site-cms/{sid}/history", headers=w).json()["history"]
    assert [h["summary"] for h in hist][:2] == ["Diwali ki mithai 2026", "Diwali ki mithai"] and hist[0]["by"] == "pub"
    assert c.post(f"/api/site-cms/{sid}/history/{hist[0]['id']}/restore", headers=e2).status_code == 403   # publisher only
    c.post(f"/api/site-cms/{sid}/history/{hist[0]['id']}/restore", headers=p)
    assert next(x for x in BL.posts(sid) if x["slug"] == post["slug"])["title"] == "Diwali ki mithai"
    hist2 = c.get(f"/api/site-cms/{sid}/history", headers=w).json()["history"]
    assert hist2[0]["action"] == "restore" and len(hist2) == 3                       # nothing lost: the restore is history too
    # a writer sees only their own drafts (and published ones); her console sees everything
    assert all(x["author"] in ("",) or x["status"] == "published" or x["author_name"] == "wri"
               for x in c.get(f"/api/site-cms/{sid}/home", headers=w).json()["drafts"])
    assert len(c.get(f"/api/sites/{sid}/cms").json()["drafts"]) == 2


def test_page_words_conflicts_and_schedule(site_env):
    from app.db import now
    from app.main import app
    from app.site import cms as CM
    from app.site import service as S
    c = TestClient(app)
    sid = _site(S, shop=False)
    toks = _team(c, sid)
    w, e1, p = (_h(toks[k]) for k in ("writer", "editor", "publisher"))
    texts = c.get(f"/api/site-cms/{sid}/page/home", headers=w).json()["texts"]
    assert texts and all(t["kind"] in ("text", "link") for t in texts)
    t0, t1 = texts[0], texts[1]
    d = c.post(f"/api/site-cms/{sid}/drafts", json={"kind": "page", "target": "home",
                                                    "ops": [{"key": t0["key"], "e": t0["e"], "value": "Akola ki sabse purani dukaan"}]},
               headers=w).json()
    assert d["ops"][0]["was"] == t0["text"]
    bad = c.post(f"/api/site-cms/{sid}/drafts", json={"kind": "page", "target": "home",
                                                      "ops": [{"key": "home__nope", "e": "1", "value": "x"}]}, headers=w)
    assert bad.status_code == 400                                                    # only real page texts
    for to, h in (("review", w), ("approved", e1), ("published", p)):
        c.post(f"/api/site-cms/{sid}/drafts/{d['id']}/move", json={"to": to}, headers=h)
    secs = S._sections(S._load(sid))
    assert "Akola ki sabse purani dukaan" in secs[t0["key"]]["html"]
    # a second draft written against the OLD text of t1, then t1 changes under it: never silently overwritten
    d2 = c.post(f"/api/site-cms/{sid}/drafts", json={"kind": "page", "target": "home",
                                                     "ops": [{"key": t1["key"], "e": t1["e"], "value": "Draft words"}]}, headers=w).json()
    S.edit_element(T, sid, t1["key"], t1["e"], "text", "Her own new words")
    for to, h in (("review", w), ("approved", e1)):
        c.post(f"/api/site-cms/{sid}/drafts/{d2['id']}/move", json={"to": to}, headers=h)
    r = c.post(f"/api/site-cms/{sid}/drafts/{d2['id']}/move", json={"to": "published"}, headers=p)
    assert r.status_code == 409 and "Her own new words" in r.json()["error"]
    assert "Her own new words" in S._sections(S._load(sid))[t1["key"]]["html"]
    # restore the first page change: the old words come back
    hist = CM.history(sid, "page", "home")
    CM.restore(sid, hist[0]["id"], CM.Who(owner=True, site_id=sid))
    assert t0["text"] in S._sections(S._load(sid))[t0["key"]]["html"]
    # scheduled: approved, a time in the future, published by the worker at that time (not before)
    d3 = c.post(f"/api/site-cms/{sid}/drafts", json={"kind": "post", "title": "Holi offer", "body": "Gujiya 20% kam."}, headers=w).json()
    for to, h in (("review", w), ("approved", e1)):
        c.post(f"/api/site-cms/{sid}/drafts/{d3['id']}/move", json={"to": to}, headers=h)
    when = (now() + timedelta(days=2)).astimezone().replace(microsecond=0).isoformat()
    assert c.post(f"/api/site-cms/{sid}/drafts/{d3['id']}/move", json={"to": "scheduled", "when": "2020-01-01T10:00"},
                  headers=p).status_code == 400
    assert c.post(f"/api/site-cms/{sid}/drafts/{d3['id']}/move", json={"to": "scheduled", "when": when}, headers=p).json()["status"] == "scheduled"
    assert CM.tick() == 0
    assert CM.tick(now() + timedelta(days=3)) == 1
    assert CM.draft(sid, CM.Who(owner=True, site_id=sid), d3["id"])["status"] == "published"
    assert CM.history(sid, "post")[0]["by"] == "pub"


def test_console_has_the_team_box():
    from pathlib import Path
    con = (Path(__file__).resolve().parents[1] / "app" / "static/console/build.js").read_text()
    assert "async function teamBox" in con and "/cms/invite" in con and "/cms/history/" in con
