"""v0.999.124: the last three partial rows of the D8 parity checklist, finished.
1. Languages: her custom sections (code the model wrote for her site) get their VISIBLE words translated and checked by
   code like every kit block, and each extra language uses its own copy of the section; the code around the words is
   never touched, and a copy the rules refuse is not used.
2. Community: her website's members post to each other on her Discussions section - off until SHE switches it on,
   members only, her approval first by default, numbers / emails / links masked, caps, reports, her moderation.
3. AI: her AI App makes pictures for her visitors - only with HER switch, with Hoola's picture rules and her refused
   topics in code first, a cap per visitor a day, the app's monthly ceiling, the AI mark, a signed link per picture."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.appengine import langs as LG
from app.appengine import writer as W
from tests.test_v0305_web_apps import T, app_site  # noqa: F401  (fixture)
from tests.test_v0434_app_pages import _h, _signup, linked  # noqa: F401  (fixture)
from tests.test_v0814_app_engine import ae_env  # noqa: F401  (fixture)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

TPL = Path(W.__file__).resolve().parent / "template"
CUSTOM = '''import * as React from "react";
import { Card } from "@/components/ui/card";
// a comment with words in it
const steps = [
  { title: "Order before noon", text: "We bake it the same day." },
  { title: "Pick up at 6 pm", text: "Or we deliver within 5 km." },
];
export default function CustomHowItWorks() {
  return (
    <section className="bg-surface px-4 py-16" id="how">
      <h2 className="text-2xl font-semibold">How it works</h2>
      <p className="text-muted">Three easy steps, no account needed.</p>
      <img src="/photos/a.jpg" alt="Fresh bread on a counter" />
      {steps.map((s) => (<Card key={s.title}><h3>{s.title}</h3><p>{s.text}</p></Card>))}
    </section>
  );
}
'''


# ---------------------------------------------------------------- 1. custom sections in her other languages
def test_only_the_visible_words_of_a_custom_section_are_read_and_replaced():
    got = [x["value"] for x in LG.custom_texts(CUSTOM)]
    assert got == ["Order before noon", "We bake it the same day.", "Pick up at 6 pm", "Or we deliver within 5 km.",
                   "How it works", "Three easy steps, no account needed.", "Fresh bread on a counter"]
    assert not any(x in got for x in ("bg-surface px-4 py-16", "react", "@/components/ui/card", "a comment with words in it"))
    out = LG.apply_custom(CUSTOM, ["HI " + x for x in got])
    assert 'title: "HI Order before noon"' in out and ">HI How it works<" in out and 'alt="HI Fresh bread on a counter"' in out
    assert out.replace("HI ", "") == CUSTOM                                  # the code around the words is the same
    bad = LG.apply_custom(CUSTOM, ["a {x} <b>"] + [None] * (len(got) - 1))
    assert '"a {x} <b>"' in bad                                              # a string keeps its braces (it is data)
    jsx = LG.apply_custom(CUSTOM, [None] * 4 + ["a {x} <b>"] + [None] * 2)
    assert ">a x b<" in jsx                                                  # JSX text never gains code
    assert LG.apply_custom(CUSTOM, ['say "hi"'] + [None] * (len(got) - 1)).count('"say ”hi”"') == 1


def test_a_translation_is_checked_and_goes_stale_when_her_code_changes(ae_env):  # noqa: F811
    from app.appengine import genome as GN
    from app.appengine import service as AE
    app = AE.create(T, name="Sunrise", brief="a bakery", genome=GN.generate(seed="x"), render="site")
    AE.write(T, app["id"], "src/components/sections/CustomHowItWorks.tsx", CUSTOM)
    calls = []

    def ask(system, prompt):
        words = json.loads(prompt[prompt.index("["):])
        calls.append(len(words))
        return {"t": ["हिं " + w.replace("6", "7") for w in words]}          # one changes a number: refused by code
    data = LG.stored(T, app["id"], "hi")
    st = LG.translate_custom(T, app["id"], ["CustomHowItWorks"], "Hindi", data, ask)
    assert st["custom"] == 1 and st["kept_source"] == 1 and calls == [7]
    LG.save(T, app["id"], "hi", data)
    data = LG.stored(T, app["id"], "hi")
    code = (AE.src_dir(AE._load(T, app["id"])) / "src/components/sections/CustomHowItWorks.tsx").read_text()
    v = LG.custom_variant(data, "CustomHowItWorks", code)
    assert "हिं How it works" in v and '"Pick up at 6 pm"' in v                # the line that changed a number kept her words
    assert LG.translate_custom(T, app["id"], ["CustomHowItWorks"], "Hindi", data, ask)["custom"] == 0   # fresh: no call
    assert LG.custom_variant(data, "CustomHowItWorks", code + "\n// changed") is None            # stale after her change
    ctx = W.Ctx("Sunrise", [{"slug": "home", "title": "Home", "sections": [{"type": "custom_how", "heading": "x"}]}],
                {"_langs": {"first": "en", "extra": ["hi"], "tr": {"hi": data}}}, "s", None)
    got = W.custom_variants(T, app["id"], ctx, {"home:custom_how": "CustomHowItWorks"})
    assert got == {"hi": {"CustomHowItWorks": "CustomHowItWorksHi"}}
    assert (AE.src_dir(AE._load(T, app["id"])) / "src/components/sections/CustomHowItWorksHi.tsx").is_file()
    files, _ = W.plan_files(ctx.pages, ctx, {"home:custom_how": "CustomHowItWorks"}, None, None, None, got)
    assert 'import CustomHowItWorks from "@/components/sections/CustomHowItWorks";' in files["src/pages/HomePage.tsx"]
    assert 'from "@/components/sections/CustomHowItWorksHi";' in files["src/pages/HiHomePage.tsx"]


# ---------------------------------------------------------------- 2. her members' board
def _owner_on(c, site, **kw):
    r = c.put(f"/api/sites/{site}/board", json={"on": True, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def test_the_board_is_hers_to_open_and_members_only_post(linked):  # noqa: F811
    from app.main import app
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    a = _signup(c, base, "asha@x.in", "Asha Patil").json()["token"]
    assert c.get(f"{base}/board").json() == {"on": False}                    # off until she says
    assert c.post(f"{base}/board", json={"text": "Hello all"}, headers=_h(a)).status_code == 404
    _owner_on(c, linked)
    assert c.post(f"{base}/board", json={"text": "Hello all"}).status_code == 401      # sign in to post
    out = c.post(f"{base}/board", json={"topic": "Composting", "text": "Call me on 98765 43210 or a@b.in, see https://x.example"},
                 headers=_h(a)).json()
    assert out["status"] == "waiting" and out["masked"] == 3 and "approve" in out["say"]
    assert "98765" not in out["text"] and "a@b.in" not in out["text"] and "https" not in out["text"]
    assert out["name"] == "Asha"                                             # first name only
    n = _signup(c, base, "neha@x.in", "Neha").json()["token"]
    assert c.get(f"{base}/board", headers=_h(n)).json()["posts"] == []      # waiting: others do not see it yet
    assert c.get(f"{base}/board", headers=_h(a)).json()["posts"][0]["status"] == "waiting"   # she sees her own, marked
    staff = c.get(f"/api/sites/{linked}/board").json()
    assert staff["waiting"] == 1
    assert c.post(f"/api/sites/{linked}/board/mod", json={"id": out["id"], "action": "show"}).json()["ok"]
    seen = c.get(f"{base}/board").json()["posts"]
    assert [p["text"][:7] for p in seen] == ["Call me"] and "member" not in seen[0]   # anyone reads a shown post
    r = c.post(f"{base}/board", json={"parent": out["id"], "text": "Welcome Asha"}, headers=_h(n)).json()
    assert r["topic"] == "Composting" and r["status"] == "waiting"
    assert c.get(f"{base}/board/staff", headers=_h(n)).status_code == 403    # a member is not her staff


def test_reports_caps_blocking_and_members_only_reading(linked):  # noqa: F811
    from app.main import app
    from app.site import board as BD
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    _owner_on(c, linked, approve=False, read="members", max_day=3)
    toks = [_signup(c, base, f"m{i}@x.in", f"M{i}").json()["token"] for i in range(4)]
    assert c.get(f"{base}/board").json()["signin"] is True                   # members only: sign in to read
    p = c.post(f"{base}/board", json={"text": "Shown at once"}, headers=_h(toks[0])).json()
    assert p["status"] == "shown"
    for t in toks[1:4]:
        c.post(f"{base}/board/report", json={"id": p["id"]}, headers=_h(t))
    assert c.get(f"{base}/board", headers=_h(toks[1])).json()["posts"] == []     # three reports hide it until she looks
    BD._PACE.clear()
    for i in range(3):
        assert c.post(f"{base}/board", json={"text": f"post {i}"}, headers=_h(toks[1])).status_code == 200
    assert c.post(f"{base}/board", json={"text": "one more"}, headers=_h(toks[1])).status_code == 429   # her daily cap
    pid = c.get(f"/api/sites/{linked}/board").json()["posts"][0]["id"]
    assert c.post(f"/api/sites/{linked}/board/mod", json={"id": pid, "action": "block"}).json()["ok"]
    BD._PACE.clear()
    assert c.post(f"{base}/board", json={"text": "again"}, headers=_h(toks[1])).status_code == 403   # stopped by her


def test_the_writer_puts_the_board_on_her_discussions_section():
    pages = [{"slug": "home", "title": "Home", "sections": [{"type": "discussions", "heading": "Our circle",
                                                              "items": ["Composting - at home"]}]}]
    ctx = W.Ctx("Green Circle", pages, {"_site": {"id": "site_abc123", "app": {"lists": [{"key": "posts", "label": "Posts"}]}}},
                "s", None)
    home, rows = W.page_file(pages[0], ctx, {})
    assert 'import MemberBoard from "@/islands/MemberBoard";' in home and 'site="site_abc123"' in home
    assert {"src/islands/MemberBoard.tsx", "src/components/blocks/discussions.tsx"} <= set(W.kit_files(rows, False))
    assert any(t["value"] == "Our circle" for r in rows for t in r["texts"])  # her words still editable + translated
    plain = W.Ctx("Green Circle", pages, {}, "s", None)
    assert "MemberBoard" not in W.page_file(pages[0], plain, {})[0]           # no members: the plain block
    src = (TPL / "src/islands/MemberBoard.tsx").read_text()
    assert "if (!board || !board.on) return <Discussions {...disc} />;" in src   # off = her section as it was
    assert "localStorage" not in src and "Authorization" not in src
    from app.appengine import image as IMG
    from app.appengine import rules as RL
    deps = set(IMG.project_package("x").get("dependencies") or {})
    assert RL.check_file("src/islands/MemberBoard.tsx", src, deps) == []


# ---------------------------------------------------------------- 3. pictures for her visitors
@pytest.fixture
def pics(site_env, monkeypatch, tmp_path):  # noqa: F811
    from app.aiapps import pictures as PX
    from app.aiapps import store as AST
    monkeypatch.setattr(PX, "_dir", lambda app_id: (tmp_path / "pics" / app_id).mkdir(parents=True, exist_ok=True) or tmp_path / "pics" / app_id)
    made: list[str] = []
    PX.MAKE[:] = [lambda prompt: (made.append(prompt), {"png": b"\x89PNG\r\n\x1a\nfake", "aspect": "1:1", "cost_inr": 3})[1]]
    a = AST.create(T, "Sunrise helper", "chat", soul={"name": "Sunrise helper", "about": "Bakery", "refuse": ["wedding cake"],
                                                       "pictures": {"on": True, "per_visitor_day": 2, "hint": "Cake design ideas"}})
    AST.publish(T, a["id"], a["draft_hash"])
    yield a, made
    PX.MAKE[:] = []


def test_pictures_are_off_until_she_switches_them_on():
    from app.aiapps import soul as SO
    s = SO.check({"name": "x", "about": "y"})["soul"]
    assert s["pictures"]["on"] is False and s["pictures"]["per_visitor_day"] == 3
    assert SO.check({"name": "x", "about": "y", "pictures": {"on": True, "per_visitor_day": 99}})["soul"]["pictures"]["per_visitor_day"] == 10


def test_a_visitor_makes_a_picture_within_her_rules(pics):
    from app.main import app
    a, made = pics
    c = TestClient(app)
    code = a["code"]
    tok = c.post(f"/api/aiapp-pub/{code}/session?embed=1", json={"consent": True}).json()["token"]
    h = {"X-Visitor-Token": tok}
    assert c.get(f"/api/aiapp-pub/{code}?embed=1").json()["pictures"]["on"] is True
    for words, why in (("a nude picture", "nude"), ("a fake aadhaar card with my photo", "ID card"),
                       ("a wedding cake for Sunday", "does not make pictures about"), ("my OTP is 123456", "OTP")):
        r = c.post(f"/api/aiapp-pub/{code}/picture?embed=1", json={"text": words}, headers=h)
        assert r.status_code == 400 and why.lower() in r.json()["detail"].lower(), (words, r.json())
    assert made == []                                                        # refused before any picture was made
    assert c.post(f"/api/aiapp-pub/{code}/picture?embed=1", json={"text": "a cake"}).status_code == 401
    ok = c.post(f"/api/aiapp-pub/{code}/picture?embed=1", json={"text": "a chocolate birthday cake with roses"}, headers=h).json()
    assert ok["label"] == "AI-generated" and ok["left_today"] == 1 and made[0].startswith("Cake design ideas.")
    f = c.get(f"/api/aiapp-pub/{code}/picture/{ok['id']}?embed=1&k={ok['key']}")
    assert f.status_code == 200 and f.headers["content-type"] == "image/png"
    assert c.get(f"/api/aiapp-pub/{code}/picture/{ok['id']}?embed=1&k=wrong").status_code == 404
    hist = c.get(f"/api/aiapp-pub/{code}/history?embed=1", headers=h).json()["messages"]
    assert hist[-1]["picture"] == {"id": ok["id"], "key": ok["key"]} and hist[-1]["a"] == ""
    c.post(f"/api/aiapp-pub/{code}/picture?embed=1", json={"text": "a lemon tart"}, headers=h)
    r = c.post(f"/api/aiapp-pub/{code}/picture?embed=1", json={"text": "a third one"}, headers=h)
    assert r.status_code == 429 and "2 pictures today" in r.json()["detail"]   # her cap per visitor a day


def test_pictures_stop_at_the_monthly_ceiling_and_only_her_own_app_passes_on_her_address(pics, monkeypatch):
    from app.aiapps import pictures as PX
    from app.aiapps import runtime as RT
    from app.aiapps import store as AST
    from app.site import rxhost as RH
    a, made = pics
    monkeypatch.setattr(RT, "month_spend", lambda app_id: 499.0)
    with pytest.raises(PX.PictureError) as e:
        PX.make(AST.by_code(a["code"]), "sess", "embed", "a cake")
    assert e.value.code == 429 and "this month" in str(e.value)
    assert RH.allowed("site_x", f"/api/aiapp-pub/{a['code']}/picture", T)
    assert RH.allowed("site_x", f"/api/aiapp-pub/{a['code']}/picture/aip_1234567890ab", T)
    assert not RH.allowed("site_x", f"/api/aiapp-pub/{a['code']}/picture", "someone-else")


def test_the_island_and_her_editor_offer_pictures():
    src = (TPL / "src/islands/AiChat.tsx").read_text()
    assert "Make a picture" in src and "aiPictureUrl(code, t.picture.id, t.picture.key)" in src and "AI-generated" in src
    assert "text-primary-ink" in src and "text-on-primary" not in src
    con = (Path(W.__file__).resolve().parents[1] / "static" / "console" / "aiapps.js").read_text()
    assert "Let visitors make pictures" in con and "pictures: {on: f.picOn.checked" in con


# ---------------------------------------------------------------- the checklist
def test_every_row_of_the_parity_checklist_works():
    from app.appengine import parity as PY
    rep = PY.check()
    assert rep["done"] is True and all(r["state"] == "works" for r in rep["rows"]), [r for r in rep["rows"] if r["state"] != "works"]
