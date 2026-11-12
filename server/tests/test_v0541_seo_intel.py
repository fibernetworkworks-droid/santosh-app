"""v0.541 SEO INTEL: tracked keywords from Search Console (+ exact positions via DataForSEO), AI visibility through the
OpenAI / Gemini / Perplexity APIs, the Google Maps grid (Places API, ids only per point), DataForSEO competitors / gap /
backlinks with her sealed login and a monthly ceiling. Every vendor is a mock transport."""
import base64
import json
from datetime import timedelta

import httpx
import pytest

T = "default"
SEEN: list[tuple[str, dict]] = []


def vendor(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    body = json.loads(req.content or b"null")
    SEEN.append((u, {"headers": dict(req.headers), "body": body}))
    if u.startswith("https://api.openai.com/v1/responses"):
        return httpx.Response(200, json={"output": [{"type": "message", "content": [{"type": "output_text",
            "text": "The best dental clinics in Akola are Smile Care and Sharma Dental (https://sharmadental.example).",
            "annotations": [{"type": "url_citation", "url": "https://www.justdial.com/akola/dentists", "title": "Justdial"},
                            {"type": "url_citation", "url": "https://sharmadental.example/implants", "title": "Sharma"}]}]}]})
    if "generativelanguage.googleapis.com" in u:
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Try Smile Care Dental for implants."}]},
            "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/x",
                                                               "title": "practo.com"}}]}}]})
    if u.startswith("https://api.perplexity.ai"):
        return httpx.Response(200, json={"choices": [{"message": {"content": "SHARMA DENTAL is well rated; also Smile Care."}}],
                                         "search_results": [{"url": "https://www.practo.com/akola", "title": "Practo"}]})
    if u.startswith("https://places.googleapis.com"):
        fm = req.headers.get("x-goog-fieldmask", "")
        q = body["textQuery"]
        if "displayName" in fm and "formattedAddress" in fm:
            return httpx.Response(200, json={"places": [{"id": "ME", "displayName": {"text": "Sharma Dental"},
                                                         "formattedAddress": "Akola", "location": {"latitude": 20.7, "longitude": 77.0}}]})
        lat = ((body.get("locationBias") or {}).get("circle") or {}).get("center", {}).get("latitude", 20.7)
        ids = ["ME", "B", "C"] if lat >= 20.7 else ["B", "C"]
        if "displayName" in fm:
            return httpx.Response(200, json={"places": [{"id": i, "displayName": {"text": {"ME": "Sharma Dental"}.get(i, "Clinic " + i)}}
                                                        for i in ids]})
        assert fm == "places.id", fm
        return httpx.Response(200, json={"places": [{"id": i} for i in ids]})
    if u.startswith("https://api.dataforseo.com"):
        auth = req.headers.get("authorization", "")
        if base64.b64decode(auth.split()[1]).decode() != "meghana@example.in:dfs-secret-pw":
            return httpx.Response(401, json={"status_code": 40100, "status_message": "Not authorized"})
        path = u.split("api.dataforseo.com")[1]
        if path == "/v3/appendix/user_data":
            return httpx.Response(200, json={"status_code": 20000, "tasks": [{"status_code": 20000, "result": [{"money": {"balance": 49.5}}]}]})
        task = body[0]
        if path.endswith("ranked_keywords/live"):
            items = ([{"keyword_data": {"keyword": "dental implants akola", "keyword_info": {"search_volume": 320}},
                       "ranked_serp_element": {"serp_item": {"rank_group": 4, "url": "https://smilecare.example/implants"}}},
                      {"keyword_data": {"keyword": "braces cost akola", "keyword_info": {"search_volume": 900}},
                       "ranked_serp_element": {"serp_item": {"rank_group": 2, "url": "https://smilecare.example/braces"}}},
                      {"keyword_data": {"keyword": "root canal", "keyword_info": {"search_volume": 5000}},
                       "ranked_serp_element": {"serp_item": {"rank_group": 35, "url": "https://smilecare.example/rct"}}}]
                     if task["target"] == "smilecare.example" else
                     [{"keyword_data": {"keyword": "dental implants akola", "keyword_info": {"search_volume": 320}},
                       "ranked_serp_element": {"serp_item": {"rank_group": 7, "url": "https://sharmadental.example/implants"}}}])
            return httpx.Response(200, json={"status_code": 20000, "cost": 0.011, "tasks": [{"status_code": 20000, "result": [{"items": items}]}]})
        if path.endswith("serp/google/organic/live/advanced"):
            return httpx.Response(200, json={"status_code": 20000, "cost": 0.002, "tasks": [{"status_code": 20000, "result": [{"items": [
                {"type": "local_pack"}, {"type": "organic", "rank_group": 1, "domain": "www.practo.com", "url": "https://www.practo.com/x", "title": "Practo"},
                {"type": "organic", "rank_group": 2, "domain": "smilecare.example", "url": "https://smilecare.example", "title": "Smile"},
                {"type": "organic", "rank_group": 3, "domain": "sharmadental.example", "url": "https://sharmadental.example/implants", "title": "Sharma"}]}]}]})
        if path.endswith("backlinks/summary/live"):
            return httpx.Response(200, json={"status_code": 20000, "cost": 0.02, "tasks": [{"status_code": 20000, "result": [
                {"rank": 120, "backlinks": 340, "referring_domains": 41, "broken_backlinks": 3}]}]})
        if path.endswith("backlinks/referring_domains/live"):
            return httpx.Response(200, json={"status_code": 20000, "cost": 0.02, "tasks": [{"status_code": 40204,
                "status_message": "Access denied. Visit Plans and Subscriptions to activate your subscription."}]})
        if path.endswith("domain_rank_overview/live"):
            return httpx.Response(200, json={"status_code": 20000, "cost": 0.01, "tasks": [{"status_code": 20000, "result": [{"items": [
                {"metrics": {"organic": {"count": 54, "etv": 210.4, "pos_1": 2, "pos_2_3": 5, "pos_4_10": 9}}}]}]}]})
        if path.endswith("competitors_domain/live"):
            return httpx.Response(200, json={"status_code": 20000, "cost": 0.01, "tasks": [{"status_code": 20000, "result": [{"items": [
                {"domain": "sharmadental.example", "intersections": 99}, {"domain": "smilecare.example", "intersections": 12, "avg_position": 6.2,
                                                                         "full_domain_metrics": {"organic": {"count": 80, "etv": 410}}}]}]}]})
    return httpx.Response(404, json={"error": "unhandled " + u})


@pytest.fixture
def I(env, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-sealing-0123456789")
    get_settings.cache_clear()
    st = get_settings()
    for k, v in {"openai_api_key": "sk-test", "gemini_api_key": "g-test", "perplexity_api_key": "p-test",
                 "google_maps_api_key": "maps-test"}.items():
        monkeypatch.setattr(st, k, v)
    from app.seo import dfs, intel
    from app.seo import service as S
    client = httpx.Client(transport=httpx.MockTransport(vendor))
    intel.set_http(client)
    dfs.set_http(client)
    SEEN.clear()
    S.save_site(T, "https://sharmadental.example", "Sharma Dental", services=["Dental implants", "Braces"], city="Akola")
    yield intel
    intel.set_http(None)
    dfs.set_http(None)


def test_mentions_are_whole_words_not_urls():
    from app.seo.intel import mention_at, score_answer
    assert mention_at("Visit https://sharmadental.example today", ["sharmadental"]) is None
    assert mention_at("Sharma Dentalcare is new", ["Sharma Dental"]) is None
    assert mention_at("Try SHARMA   dental", ["Sharma Dental"]) == 4
    assert mention_at("Café Mocha", ["Cafe Mocha"]) == 0
    sc = score_answer("Smile Care first, then Sharma Dental.", [{"url": "https://x.in/a", "title": "", "domain": "x.in"}],
                      ["Sharma Dental"], {"smilecare.example": ["Smile Care"]}, "sharmadental.example")
    assert sc["mentioned"] and sc["rank"] == 2 and sc["brands"] == ["smilecare.example"] and not sc["cited"]


def test_track_and_search_console_positions(I, monkeypatch):
    from app.seo import service as S
    I.track(T, ["Dental Implants Akola", "braces akola", "dental implants akola"])
    assert I.tracked(T, I._site(T)["id"]) == ["dental implants akola", "braces akola"]
    calls = []
    end = S.today(T) - timedelta(days=3)

    def gsc(tenant, method, path, body):
        calls.append(body)
        rx = body["dimensionFilterGroups"][0]["filters"][0]
        assert rx["operator"] == "includingRegex" and rx["expression"].startswith("^(")
        rows = []
        for i, pos in enumerate((12.0, 4.0)):         # a week ago 12th, now 4th
            d = (end - timedelta(days=7 * (1 - i))).isoformat()
            rows.append({"keys": [d, "dental implants akola", "https://sharmadental.example/implants"], "clicks": 3, "impressions": 100, "position": pos})
        rows.append({"keys": [end.isoformat(), "braces akola", "https://sharmadental.example/braces"], "clicks": 1, "impressions": 50, "position": 3})
        rows.append({"keys": [(end - timedelta(days=7)).isoformat(), "braces akola", "https://sharmadental.example/"], "clicks": 0, "impressions": 30, "position": 1})
        rows.append({"keys": [end.isoformat(), "something else", "/"], "clicks": 9, "impressions": 9, "position": 1})
        return {"rows": rows}
    monkeypatch.setattr(S, "_gsc", gsc)
    monkeypatch.setattr(S, "_auto_property", lambda t, s="": "sc-domain:sharmadental.example")
    r = I.pull_gsc(T, days=14)
    assert r["rows"] == 4
    v = {k["keyword"]: k for k in I.ranks_view(T)["keywords"]}
    assert v["dental implants akola"]["position"] == 4.0 and v["dental implants akola"]["move_7d"] == 8.0
    assert v["braces akola"]["move_7d"] == -2.0
    assert "something else" not in v
    I.track(T, ["root canal"])
    with S.session() as s:
        from app.seo.intel import SeoRank
        s.add(SeoRank(tenant_id=T, site_id=I._site(T)["id"], keyword="root canal", day=(end - timedelta(days=7)).isoformat(), position=3))
        s.add(SeoRank(tenant_id=T, site_id=I._site(T)["id"], keyword="root canal", day=end.isoformat(), position=11))
    assert any("root canal" in a and "8.0" in a for a in I.rank_alerts(T))


def test_ai_visibility_three_engines_scored_and_capped(I, monkeypatch):
    from app.seo import desk
    from app.seo.desk import SeoDesk
    with I.session() if hasattr(I, "session") else __import__("app.db", fromlist=["session"]).session() as s:
        s.add(SeoDesk(site_id=I._site(T)["id"], tenant_id=T, competitors=json.dumps(["smilecare.example", "Smile Care"])))
    assert desk  # imported for the table
    with pytest.raises(I.IntelError):
        I.run_ai(T)                                          # no questions yet
    I.add_prompts(T, ["Best dental clinic in Akola for implants?", "Braces cost in Akola", "x"])
    assert len(I.prompts(T)) == 2                            # too-short question dropped
    r = I.run_ai(T)
    assert r["answers"] == 6 and r["errors"] == 0 and r["cost_inr"] == 12.0
    be = r["by_engine"]
    assert be["openai"]["mentioned_pct"] == 100 and be["openai"]["cited_pct"] == 100
    assert be["gemini"]["mentioned_pct"] == 0 and be["perplexity"]["mentioned_pct"] == 100
    assert dict(r["cited_instead"])["practo.com"] == 4 and "justdial.com" in dict(r["cited_instead"])
    assert dict(r["competitors_named"])["Smile Care"] == 6
    oa = [x for x in SEEN if "openai" in x[0]][0][1]
    assert oa["body"]["tools"] == [{"type": "web_search"}] and oa["headers"]["authorization"] == "Bearer sk-test"
    gm = [x for x in SEEN if "generativelanguage" in x[0]][0][1]
    assert gm["body"]["tools"] == [{"google_search": {}}]
    I.save_settings(T, ai_cap_inr=15)
    with pytest.raises(I.IntelError) as e:
        I.run_ai(T)                                          # 12 spent + 12 needed > 15
    assert "limit" in str(e.value)


def test_suggested_questions_never_name_her(I, monkeypatch):
    from app.net import ai
    monkeypatch.setattr(ai, "llm", lambda *a, **k: '["Best dentist in Akola?", "Is Sharma Dental good?", "Implant cost Akola"]')
    s = I.suggest_prompts(T)["suggestions"]
    assert s == ["Best dentist in Akola?", "Implant cost Akola"]


def test_maps_grid_ids_only_per_point(I):
    with pytest.raises(I.IntelError):
        I.run_grid(T, "dentist")                             # her shop not picked yet
    c = I.find_place(T)["candidates"]
    assert c[0]["id"] == "ME"
    I.choose_place(T, c[0])
    g = I.run_grid(T, "dentist near me", size=3, km=1.5)
    assert len(g["points"]) == 9 and g["found"] == 6 and g["top3"] == 6       # the south row: not in the first 20
    north = g["points"][0]
    assert north["lat"] > 20.7 and north["rank"] == 1
    assert g["leaders"][0]["you"] is True
    cnt = [x for x in SEEN if x[0].startswith("https://places.googleapis.com") and x[1]["headers"].get("x-goog-fieldmask") == "places.id"]
    assert len(cnt) == 9
    assert I.grids_view(T)["grids"][0]["keyword"] == "dentist near me"


def test_dataforseo_login_sealed_costed_capped(I):
    from app.seo import dfs
    sid = I._site(T)["id"]
    with pytest.raises(dfs.DfsError):
        dfs.competitors(T, sid, "sharmadental.example")      # not joined
    with pytest.raises(dfs.DfsError) as e:
        dfs.save_login(T, sid, "meghana@example.in", "wrong-pass")
    assert "login nahi maana" in str(e.value)
    r = dfs.save_login(T, sid, "meghana@example.in", "dfs-secret-pw")
    assert r["balance_usd"] == 49.5 and "dfs-secret-pw" not in json.dumps(I.view(T))
    comp = dfs.competitors(T, sid, "sharmadental.example")
    assert [c["domain"] for c in comp] == ["smilecare.example"] and comp[0]["traffic"] == 410
    g = dfs.gap(T, sid, "sharmadental.example", "https://www.smilecare.example/")
    assert [x["keyword"] for x in g["gap"]] == ["braces cost akola"]   # implants: she is 7th already; root canal: they are 35th
    with pytest.raises(dfs.DfsError) as e:
        dfs.backlinks(T, sid, "sharmadental.example")
    assert "subscription" in str(e.value)
    I.track(T, ["dental implants akola"])
    r = I.check_serp(T)
    assert r["results"][0]["position"] == 3 and r["results"][0]["top"][0]["domain"] == "practo.com"
    st = dfs.status(T, sid)
    assert st["spent_usd"] == pytest.approx(0.01 + 0.011 * 2 + 0.02 * 2 + 0.002, abs=1e-6) and st["via"] == "own"
    I.save_settings(T, dfs_cap_usd=0.5)
    with I.session() if hasattr(I, "session") else __import__("app.db", fromlist=["session"]).session() as s:
        from app.seo.intel import SeoIntel
        row = s.get(SeoIntel, sid)
        sp = json.loads(row.spend)
        for m in sp.values():
            m["dfs_usd"] = 0.5
        row.spend = json.dumps(sp)
    with pytest.raises(dfs.DfsError) as e:
        dfs.domain_overview(T, sid, "sharmadental.example")
    assert "seema" in str(e.value)
    dfs.forget_login(T, sid)
    assert dfs.status(T, sid)["connected"] is False


def test_routes_and_tools(I):
    from fastapi.testclient import TestClient

    from app import main
    from app.agent import seo_tools
    with TestClient(main.app) as c:
        v = c.get("/api/seo/intel").json()
        assert v["site"]["domain"] == "sharmadental.example" and v["ai"]["engines"]["perplexity"]["ready"] is True
        assert c.post("/api/seo/intel/track", json={"keywords": ["implants akola"]}).json()["tracked"] == 1
        assert c.post("/api/seo/intel/dfs/gap", json={}).status_code == 400
        assert c.post("/api/seo/intel/dataforseo", json={"login": "meghana@example.in", "password": "dfs-secret-pw"}).json()["connected"]
        ov = c.post("/api/seo/intel/dfs/overview", json={}).json()
        assert ov["keywords"] == 54 and ov["top3"] == 7 and ov["top10"] == 16 and ov["spend"]["spent_usd"] > 0
        assert c.post("/api/seo/intel/settings", json={"grid_size": 4}).status_code == 400
        assert c.post("/api/seo/intel/ai/prompts", json={"prompts": ["Best implants clinic Akola?"]}).json()["added"] == 1
    acts = seo_tools.SEO_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    for a in ("track", "rank_check", "ai_run", "maps_grid", "gap", "backlinks"):
        assert a in acts
    assert "intel" in seo_tools.SEO_TOOLS[1]["input_schema"]["properties"]["what"]["enum"]
