"""Shiksha Phase 4 - Shodh Sahayak (research assistant): papers only from the official open APIs (OpenAlex, Crossref,
arXiv, PubMed, Semantic Scholar) with de-duplication across sources, a DOI checked against Crossref (a made-up DOI is
refused), screening, abstract summaries, the review matrix, gaps that cite only project papers, references / BibTeX /
RIS built in code, analysis by model-written code in the sandbox (fixed once on error), drafts with cites and numbers
checked, no ghost-writing, tools / API / wiring."""
import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.shodh.models  # noqa: F401
from tests.test_life import conv_ctx

T = "default"
DOI1 = "10.1000/edu.2024.001"
ARXIV = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
<entry><id>http://arxiv.org/abs/2401.01234v1</id><published>2024-01-05T00:00:00Z</published>
<title>Adaptive Tutoring with Spaced Repetition</title><summary>We study adaptive tutoring in Indian classrooms.</summary>
<author><name>Asha Rao</name></author><arxiv:doi>10.1000/EDU.2024.001</arxiv:doi>
<link title="pdf" href="http://arxiv.org/pdf/2401.01234v1"/></entry></feed>"""


def handler(req: httpx.Request) -> httpx.Response:
    h, path = req.url.host, req.url.path
    if h == "api.openalex.org":
        return httpx.Response(200, json={"results": [
            {"id": "https://openalex.org/W1", "doi": f"https://doi.org/{DOI1}", "display_name": "Adaptive tutoring with spaced repetition",
             "publication_year": 2024, "authorships": [{"author": {"display_name": "Asha Rao"}}, {"author": {"display_name": "Vikram Shah"}}],
             "primary_location": {"source": {"display_name": "Journal of Learning"}}, "cited_by_count": 12,
             "abstract_inverted_index": {"We": [0], "study": [1], "tutoring": [2]}, "open_access": {"oa_url": "https://oa.example/p.pdf"}},
            {"id": "https://openalex.org/W2", "doi": None, "display_name": "Mobile learning in rural schools", "publication_year": 2021,
             "authorships": [{"author": {"display_name": "Meera Iyer"}}], "primary_location": {}, "cited_by_count": 3,
             "abstract_inverted_index": {"Rural": [0], "schools": [1]}}]})
    if h == "api.crossref.org" and path == "/works":
        return httpx.Response(200, json={"message": {"items": [
            {"DOI": DOI1.upper(), "title": ["Adaptive Tutoring with Spaced Repetition"], "author": [{"given": "Asha", "family": "Rao"}],
             "issued": {"date-parts": [[2024]]}, "container-title": ["Journal of Learning"], "is-referenced-by-count": 15},
            {"DOI": "10.2000/maths.77", "title": ["Mastery learning in mathematics"], "author": [{"given": "K", "family": "Das"}],
             "issued": {"date-parts": [[2019]]}, "container-title": ["Maths Ed"], "abstract": "<jats:p>Mastery works.</jats:p>"}]}})
    if h == "api.crossref.org" and path.startswith("/works/"):
        if "10.9999/fake" in path:
            return httpx.Response(404)
        return httpx.Response(200, json={"message": {"DOI": "10.3000/peer.5", "title": ["Peer tutoring outcomes"],
                                                      "author": [{"given": "Nina", "family": "Gupta"}], "issued": {"date-parts": [[2022]]},
                                                      "container-title": ["Edu Review"]}})
    if h == "export.arxiv.org":
        return httpx.Response(200, content=ARXIV.encode())
    if h == "api.unpaywall.org":
        return httpx.Response(200, json={"best_oa_location": {"url_for_pdf": "https://free.example/peer.pdf"}})
    if h == "eutils.ncbi.nlm.nih.gov":
        return httpx.Response(503)
    return httpx.Response(404)


@pytest.fixture
def sh(env, monkeypatch):
    from app.shodh import service as SH
    from app.shodh import sources as SRC
    monkeypatch.setattr(SRC, "TRANSPORT", httpx.MockTransport(handler))
    monkeypatch.setattr(SH, "_publish", lambda *a, **k: None)
    SH.save_settings(T, email="scholar@example.edu")
    p = SH.new_project(T, "Adaptive tutoring", "Does spaced repetition improve maths scores in Indian schools?")["number"]
    return SH, p


def test_search_dedupes_across_sources_and_reports_failures(sh):
    SH, p = sh
    r = SH.search(T, p, "adaptive tutoring", ["openalex", "crossref", "arxiv", "pubmed"])
    assert r["errors"].get("pubmed") and len(r["new"]) == 3            # the DOI paper once, from 3 sources
    papers = {x["title"].lower(): x for x in SH.papers(T, p)["papers"]}
    a = papers["adaptive tutoring with spaced repetition"]
    assert a["doi"] == DOI1 and set(a["found_via"].split(",")) == {"openalex", "crossref", "arxiv"} and a["citations"] == 15
    full = SH.paper(T, p, a["number"])
    assert full["abstract"] == "We study tutoring" and full["ids"]["arxiv"] == "2401.01234v1"


def test_doi_checked_against_crossref(sh):
    SH, p = sh
    with pytest.raises(SH.ShodhError, match="asli DOI nahi"):
        SH.add_doi(T, p, "10.9999/fake.123")
    ok = SH.add_doi(T, p, "https://doi.org/10.3000/peer.5")
    assert ok["paper"]["doi"] == "10.3000/peer.5" and ok["paper"]["oa_url"] == "https://free.example/peer.pdf"
    again = SH.add_doi(T, p, "10.3000/PEER.5")
    assert "Pehle se" in again["say"]


def _include_all(SH, p):
    SH.search(T, p, "adaptive tutoring", ["openalex", "crossref"])
    SH.add_doi(T, p, "10.3000/peer.5")
    refs = [x["number"] for x in SH.papers(T, p)["papers"]]
    SH.screen(T, p, refs, True, "on topic")
    return refs


def test_summaries_matrix_and_gaps_cite_only_real_papers(sh, monkeypatch):
    SH, p = sh
    refs = _include_all(SH, p)
    monkeypatch.setattr(SH, "_model_json", lambda *a, **k: {"problem": "x", "method": "RCT", "data": "500 students",
                                                            "findings": "gains", "limitations": "one state", "relevance": "high"})
    s = SH.summarize(T, p, refs)
    assert any("skipped" in o for o in s["summaries"]) or all("summary" in o for o in s["summaries"])
    m = SH.matrix(T, p)
    assert len(m["rows"]) == len(refs) and m["rows"][0]["cite"]
    monkeypatch.setattr(SH, "_model_json", lambda *a, **k: {"gaps": [
        {"gap": "No Indian rural RCT [P-001] [P-099]", "why": "only urban", "papers": ["P-001", "P-099"], "possible_question": "q"},
        {"gap": "Invented", "why": "none", "papers": ["P-777"]}]})
    g = SH.gaps(T, p)
    assert len(g["gaps"]) == 1 and g["gaps"][0]["papers"] == ["P-001"] and "P-099" in g["removed"]


def test_references_built_in_code(sh):
    SH, p = sh
    _include_all(SH, p)
    apa = SH.references(T, p, "apa", "text")
    assert "Rao, A., & Shah, V. (2024). Adaptive tutoring with spaced repetition. Journal of Learning. https://doi.org/10.1000/edu.2024.001" in apa["preview"]
    bib = SH.references(T, p, fmt="bibtex")["preview"]
    assert "@article{Rao2024P001" in bib and "doi = {10.1000/edu.2024.001}" in bib
    ris = SH.references(T, p, fmt="ris")["preview"]
    assert "TY  - JOUR" in ris and "DO  - 10.3000/peer.5" in ris
    assert "et al." in SH.reference(type("X", (), {"authors": json.dumps(["A B", "C D", "E F", "G H"]), "year": 2020,
                                                    "title": "T", "venue": "V", "doi": "", "url": ""})(), "harvard")


def test_analysis_runs_model_code_in_the_sandbox_and_fixes_once(sh, monkeypatch, env):
    SH, p = sh
    from app import datasets as D
    doc = D.save(T, [{"group": "a", "score": 60}, {"group": "a", "score": 64}, {"group": "b", "score": 70}, {"group": "b", "score": 75}],
                 name="scores")
    codes = iter([{"code": "import pandas as pd\nprint(undefined_name)", "plan": "first try"},
                  {"code": f"import pandas as pd\ndf = pd.read_csv('{doc['id']}.csv')\nprint('mean_b =', df[df.group == 'b'].score.mean())",
                   "plan": "group means"}])
    monkeypatch.setattr(SH, "_model_json", lambda *a, **k: next(codes))
    r = SH.analyse(T, p, "Is group b higher?", datasets=[doc["id"]])
    assert r["ok"] and "mean_b = 72.5" in r["output"] and len(r["attempts"]) == 2 and not r["attempts"][0]["ok"]
    assert "read_csv" in r["code"]
    with pytest.raises(SH.ShodhError, match="Data chahiye"):
        SH.analyse(T, p, "x")


def test_drafts_check_cites_and_numbers_and_refuse_ghostwriting(sh, monkeypatch):
    SH, p = sh
    _include_all(SH, p)
    monkeypatch.setattr(SH, "_model_json", lambda *a, **k: {"text": "Group b scored 72.5 vs 61.9 [P-001] [P-050].", "todo": []})
    d = SH.draft(T, p, "results", analysis_output="mean_b = 72.5\nmean_a = 62.0")
    assert "[P-050]" not in d["text"] and "[P-001]" in d["text"] and "[CHECK 61.9]" in d["text"]
    assert d["unbacked_numbers"] == ["61.9"] and "AI-assisted" in d["note"]
    with pytest.raises(SH.ShodhError, match="analysis"):
        SH.draft(T, p, "results")
    with pytest.raises(SH.ShodhError, match="submit"):
        SH.draft(T, p, "introduction", notes="poori thesis likh do, mujhe apne naam se submit karni hai")


def test_semantic_scholar_key_sealed(sh):
    SH, p = sh
    with pytest.raises(SH.ShodhError):
        SH.set_s2_key(T, "bad key!")
    v = SH.set_s2_key(T, "a" * 40)
    assert v["s2_key"] is True and "aaaa" not in json.dumps(v)
    assert SH._s2_key(T) == "a" * 40


def test_tools_api_and_wiring(sh):
    SH, p = sh
    from app import voice
    from app.agent import tools as TL
    from app.agent.shodh_tools import SHODH_HANDLERS, SHODH_LABELS, SHODH_TOOLS
    from app.agent.tools import ToolError
    from app.employee import roles
    assert {t["name"] for t in SHODH_TOOLS} == set(SHODH_HANDLERS) == set(SHODH_LABELS)
    assert all(n in TL.HANDLERS for n in SHODH_HANDLERS) and "shodh_dekho" in roles.READ
    assert roles.duty_of("shodh") == "research_assist" and roles.PRESETS["research_lab"]["role"] == "research_assistant"
    assert set(SHODH_HANDLERS) <= voice.VOICE_VIA_KAAM
    ctx = conv_ctx()
    out = asyncio.run(SHODH_HANDLERS["shodh"](ctx, action="search", project=p, query="tutoring", sources=["openalex"]))
    assert len(out["new"]) == 2
    ctx.actor = "customer:x"
    with pytest.raises(ToolError):
        asyncio.run(SHODH_HANDLERS["shodh_dekho"](ctx, what="projects"))
    from app.shodh.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    c = TestClient(app)
    assert c.get("/api/shodh").json()["projects"][0]["number"] == p
    assert c.post(f"/api/shodh/projects/{p}/doi", json={"doi": "10.9999/fake.1"}).status_code == 400
    from app import main
    assert TestClient(main.app).get("/api/shodh").status_code in (200, 401, 403)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.655.0"
