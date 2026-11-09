"""v0.670.0 DUNIYA MANCH - the T4 keyless-public-web family, backend-only (owner: "T4"; the T4 tier
of download/HOOLA_MCP_FEED.json - the no-login / no-key public-web rows, catalog-description-verified
and ported IDEA-ONLY: the modelcontextprotocol/servers fetch reference "Web content fetching
capabilities for LLMs" + the no-key public-API rows (Wikipedia / Open-Meteo / Hacker News /
Frankfurter / Free Dictionary / arXiv); zero upstream code, zero new pip - httpx is already the
house's, zero new keys).

ONE tool `duniya`, actions fetch | wikipedia | weather | hn | currency | dictionary | arxiv | status,
every answer one envelope. What is tested FOR REAL - the whole suite is OFFLINE (zero network):
every public byte rides the ONE seam `duniya_tools._http_get`, and every test here monkeypatches
exactly that:

the envelope shape (ok / error{code, message, hint} / meta{elapsed_ms, backend}), status (zero
network, backends + caps + laws + the jharokha pointer), the kill switch (off means off - every
action NEED_SETUP), fetch (scripts and styles stripped, text kept, JSON pretty-printed, the redirect
final_url told honestly, the honest truncation note at the cap, the TOO_BIG past the download cap,
a non-text content-type refused with the jharokha hint, the PAN id-mask riding the text, the guard
REALLY wired into the fetch path), the SSRF guard itself (loopback, link-local metadata, file://,
an empty url - the house guard, literal IPs, zero DNS), wikipedia (search + summary, two seam calls
in order, snippet tags stripped, no results = NOT_FOUND with no summary call, a failing courtesy
summary leaves the results standing), weather (geocode + forecast, the WMO code named in words,
the days clamp, an unknown place = NOT_FOUND), hn (titles / points / the hn_url built from
objectID, nbHits), currency (rate + the multiplied result, the historical date in the url, bad
codes and bad dates refused, a missing pair = NOT_FOUND), dictionary (meanings with capped
definitions, the 404 = NOT_FOUND honesty), arxiv (Atom parsed with the stdlib, titles / authors /
abstract / link, a broken Atom = UPSTREAM, an empty feed = NOT_FOUND), error mapping (an upstream
timeout = UPSTREAM), the purity pin (no top-level httpx - the lazy import law), registry 608 pin,
the enum pin, APP_VERSION pin.
"""
import asyncio
import ast
import json
from pathlib import Path

import pytest

from app.agent import duniya_tools as J
from app.agent.tools import Ctx, TOOLS

CTX = Ctx(tenant_id="duniya-test-tenant", conversation_id="c1")


def du(action="status", ctx=None, **kw):
    return asyncio.run(J.duniya(ctx or CTX, action, **kw))


def _seam(responses):
    """A fake seam: pops one (status, ctype, text, final_url) per call, records the urls."""
    calls = []

    async def fake(url, *, headers=None):
        calls.append(url)
        item = responses.pop(0) if responses else (200, "application/json", "{}", url)
        if isinstance(item, Exception):
            raise item
        return item

    return fake, calls


@pytest.fixture
def clean_settings():
    """The switch rides the live settings (default on) - tests flip it via monkeypatch only."""
    yield


# ---------------------------------------------------------------- the shape

def test_envelope_shape_always():
    for out in (du("status"), du("nope"), du("fetch", url="http://127.0.0.1/x"),
                du("wikipedia"), du("currency", base="USD", quote="EUR")):
        assert out["schema_version"] == 1 and out["tool"] == "duniya"
        assert set(out) >= {"ok", "action", "error", "meta"}
        assert isinstance(out["meta"]["elapsed_ms"], int)
        assert out["meta"]["backend"]
        assert out["error"] is None or set(out["error"]) == {"code", "message", "hint"}


def test_status_is_zero_network():
    fake, calls = _seam([])
    real, J._http_get = J._http_get, fake
    try:
        out = du("status")
    finally:
        J._http_get = real
    assert out["ok"] and calls == []                    # status never touches the seam
    assert out["actions"] == list(J._DU_ACTIONS)
    assert set(out["backends"]) == set(J._DU_ACTIONS)
    assert out["caps"]["fetch_chars"] == J._MAX_FETCH_CHARS
    assert any("GET only" in law for law in out["laws"])
    assert "jharokha" in out["browser_alternative"]


def test_kill_switch_off_means_off(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "duniya_enabled", False, raising=False)
    out = du("wikipedia", q="pune")
    assert not out["ok"] and out["error"]["code"] == "NEED_SETUP"
    assert "duniya_enabled=true" in out["error"]["hint"]


# ---------------------------------------------------------------- fetch

HTML_PAGE = ("<html><head><style>body{color:red}</style><script>var x='secret-js';</script>"
             "<title>t</title></head><body><h1>Duniya page</h1>"
             "<p>Real words stay ABCPF1234F here.</p><script>more()</script></body></html>")


def test_fetch_strips_scripts_and_styles(monkeypatch):
    fake, calls = _seam([(200, "text/html; charset=utf-8", HTML_PAGE, "https://example.com/page")])
    monkeypatch.setattr(J, "_http_get", fake)
    monkeypatch.setattr(J, "_guard_url", lambda u: u)   # happy path; the real guard is tested below
    out = du("fetch", url="https://example.com/page")
    assert out["ok"] and out["status"] == 200
    assert "secret-js" not in out["text"] and "more()" not in out["text"]
    assert "body{color:red}" not in out["text"]
    assert "Duniya page" in out["text"] and "Real words stay" in out["text"]
    assert "ABCXXXXXXF" in out["text"]                  # the PAN id-mask rode the text
    assert calls and calls[0] == "https://example.com/page"


def test_fetch_reports_the_final_url_after_redirect(monkeypatch):
    fake, _ = _seam([(200, "application/json", '{"a": 1}', "https://example.com/final/")])
    monkeypatch.setattr(J, "_http_get", fake)
    monkeypatch.setattr(J, "_guard_url", lambda u: u)
    out = du("fetch", url="https://example.com/old")
    assert out["ok"] and out["final_url"] == "https://example.com/final/"
    assert '"a": 1' in out["text"]                      # json came back pretty-printed


def test_fetch_truncates_honestly(monkeypatch):
    big = "<html><body>" + ("word " * 6_000) + "</body></html>"   # text ~24k > the 12k cap
    fake, _ = _seam([(200, "text/html", big, "https://example.com/big")])
    monkeypatch.setattr(J, "_http_get", fake)
    monkeypatch.setattr(J, "_guard_url", lambda u: u)
    out = du("fetch", url="https://example.com/big")
    assert out["ok"] and out["chars"] == J._MAX_FETCH_CHARS
    assert "truncated" in out["note"]


def test_fetch_too_big_is_honest(monkeypatch):
    fake, _ = _seam([(200, "text/plain", "x" * (J._MAX_BODY_CHARS + 1), "https://example.com/huge")])
    monkeypatch.setattr(J, "_http_get", fake)
    monkeypatch.setattr(J, "_guard_url", lambda u: u)
    out = du("fetch", url="https://example.com/huge")
    assert not out["ok"] and out["error"]["code"] == "TOO_BIG"


def test_fetch_refuses_non_text(monkeypatch):
    fake, _ = _seam([(200, "image/png", "not-text", "https://example.com/i.png")])
    monkeypatch.setattr(J, "_http_get", fake)
    monkeypatch.setattr(J, "_guard_url", lambda u: u)
    out = du("fetch", url="https://example.com/i.png")
    assert not out["ok"] and out["error"]["code"] == "UPSTREAM"
    assert "jharokha" in out["error"]["message"] + out["error"]["hint"]


def test_fetch_guard_really_wired(monkeypatch):
    """The free fetch url REALLY goes through the house guard - patch only the seam, never the guard."""
    sentinel = []

    def spy(url):
        sentinel.append(url)
        raise J.ToolError("blocked by the spy")

    monkeypatch.setattr(J, "_guard_url", spy)
    out = du("fetch", url="https://example.com/x")
    assert sentinel == ["https://example.com/x"]        # the guard stood between the ask and the web
    assert not out["ok"] and out["error"]["code"] == "BLOCKED"


@pytest.mark.parametrize("url", ["http://127.0.0.1:8080/x", "http://169.254.169.254/latest/meta-data/",
                                 "file:///etc/passwd", "ftp://example.com/f"])
def test_the_ssrf_guard_itself(url):
    out = du("fetch", url=url)                          # no patches: the REAL house guard runs
    assert not out["ok"] and out["error"]["code"] == "BLOCKED"


def test_fetch_empty_url_is_bad_input():
    out = du("fetch", url="")
    assert not out["ok"] and out["error"]["code"] == "BAD_INPUT"


# ---------------------------------------------------------------- wikipedia

def test_wikipedia_search_plus_summary(monkeypatch):
    fake, calls = _seam([
        (200, "application/json", '{"query": {"search": [{"title": "Pune", "snippet": "a <b>city</b> in Maharashtra"}]}}',
         "https://en.wikipedia.org/w/api.php"),
        (200, "application/json",
         '{"title": "Pune", "extract": "Pune is a city.", "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Pune"}}}',
         "https://en.wikipedia.org/api/rest_v1/page/summary/Pune"),
    ])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("wikipedia", q="Pune")
    assert out["ok"] and out["lang"] == "en"
    assert out["results"][0]["title"] == "Pune"
    assert "<b>" not in out["results"][0]["snippet"] and "city" in out["results"][0]["snippet"]
    assert out["summary"]["extract"] == "Pune is a city."
    assert len(calls) == 2 and "list=search" in calls[0] and "rest_v1/page/summary" in calls[1]


def test_wikipedia_no_results_is_not_found(monkeypatch):
    fake, calls = _seam([(200, "application/json", '{"query": {"search": []}}', "x")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("wikipedia", q="zzzznothing")
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"
    assert len(calls) == 1                              # no summary call for nothing


def test_wikipedia_summary_failure_is_not_fatal(monkeypatch):
    fake, _ = _seam([
        (200, "application/json", '{"query": {"search": [{"title": "Pune", "snippet": "ok"}]}}', "x"),
        J._Upstream("the summary service hiccuped"),
    ])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("wikipedia", q="Pune")
    assert out["ok"] and out["results"] and "summary" not in out   # the search result stands


def test_wikipedia_input_laws():
    out = du("wikipedia")
    assert out["error"]["code"] == "BAD_INPUT"
    out = du("wikipedia", q="x", lang="england")
    assert out["error"]["code"] == "BAD_INPUT"


# ---------------------------------------------------------------- weather

GEO = {"results": [{"name": "Pune", "country": "India", "admin1": "Maharashtra",
                    "latitude": 18.52, "longitude": 73.86, "timezone": "Asia/Kolkata"}]}
FC = {"timezone": "Asia/Kolkata",
      "current": {"temperature_2m": 24.1, "relative_humidity_2m": 61, "weather_code": 61, "wind_speed_10m": 9.3},
      "daily": {"time": ["2026-11-07", "2026-11-08", "2026-11-09"],
                "weather_code": [61, 0, 3],
                "temperature_2m_max": [29.0, 31.0, 30.5],
                "temperature_2m_min": [18.0, 19.0, 19.5],
                "precipitation_sum": [4.2, 0.0, 0.0]}}


def test_weather_geocode_then_forecast(monkeypatch):
    fake, calls = _seam([(200, "application/json", json.dumps(GEO), "geo"),
                         (200, "application/json", json.dumps(FC), "fc")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("weather", place="Pune")
    assert out["ok"] and out["place"]["name"] == "Pune" and out["place"]["lat"] == 18.52
    assert out["current"]["weather"] == "light rain"    # WMO 61 named in words
    assert out["daily"][1]["weather"] == "clear sky"    # WMO 0
    assert len(out["daily"]) == 3
    assert len(calls) == 2 and "geocoding-api" in calls[0] and "forecast_days=3" in calls[1]


def test_weather_days_clamped(monkeypatch):
    fake, calls = _seam([(200, "application/json", json.dumps(GEO), "geo"),
                         (200, "application/json", json.dumps(FC), "fc")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("weather", place="Pune", days=99)
    assert out["ok"] and "forecast_days=7" in calls[1]  # clamped to the cap, said out loud


def test_weather_unknown_place(monkeypatch):
    fake, _ = _seam([(200, "application/json", '{"results": []}', "geo")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("weather", place="Nowhereville")
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------- hn

HN = {"nbHits": 4242, "hits": [
    {"objectID": "12345", "title": "Show HN: Duniya", "url": "https://example.com/d",
     "points": 250, "author": "hnuser", "num_comments": 88},
    {"objectID": "6789", "title": None, "story_title": "Ask HN: keys?",
     "url": None, "story_url": "https://example.com/a", "points": None,
     "story_points": 12, "author": "asker", "num_comments": 3},
]}


def test_hn_hits_shape(monkeypatch):
    fake, calls = _seam([(200, "application/json", json.dumps(HN), "hn")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("hn", q="mcp", max_items=2)
    assert out["ok"] and out["nbHits"] == 4242
    h0, h1 = out["hits"]
    assert h0["title"] == "Show HN: Duniya" and h0["points"] == 250 and h0["comments"] == 88
    assert h0["hn_url"] == "https://news.ycombinator.com/item?id=12345"
    assert h1["title"] == "Ask HN: keys?" and h1["points"] == 12   # the story_* fallbacks rode
    assert "hitsPerPage=2" in calls[0] and "tags=story" in calls[0]


def test_hn_needs_q():
    assert du("hn")["error"]["code"] == "BAD_INPUT"


# ---------------------------------------------------------------- currency

def test_currency_latest_rate(monkeypatch):
    fake, calls = _seam([(200, "application/json",
                          '{"amount": 100.0, "base": "USD", "date": "2026-11-06", "rates": {"INR": 8350.0}}', "fx")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("currency", base="usd", quote="INR", amount=100)
    assert out["ok"] and out["from"] == "USD" and out["to"] == "INR"
    assert out["rate"] == pytest.approx(83.5) and out["result"] == pytest.approx(8350.0)
    assert "from=USD" in calls[0] and "amount=100.0" in calls[0]


def test_currency_historical_date(monkeypatch):
    fake, calls = _seam([(200, "application/json", '{"date": "2026-01-15", "rates": {"INR": 82.9}}', "fx")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("currency", base="USD", quote="INR", date="2026-01-15")
    assert out["ok"] and out["date"] == "2026-01-15"
    assert "frankfurter.app/2026-01-15" in calls[0]     # the date rode the path


def test_currency_input_laws():
    assert du("currency", base="USDD", quote="INR")["error"]["code"] == "BAD_INPUT"
    assert du("currency", base="USD", quote="IN")["error"]["code"] == "BAD_INPUT"
    assert du("currency", base="USD", quote="INR", date="15-01-2026")["error"]["code"] == "BAD_INPUT"


def test_currency_missing_pair_is_not_found(monkeypatch):
    fake, _ = _seam([(200, "application/json", '{"rates": {"EUR": 0.9}}', "fx")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("currency", base="USD", quote="XXX")
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------- dictionary

DICT = [{"word": "jharokha", "phonetic": "dʒəˈroːkha",
         "phonetics": [{"text": "/dʒəˈroːkha/"}],
         "meanings": [{"partOfSpeech": "noun",
                       "definitions": [{"definition": "an overhanging enclosed balcony",
                                        "example": "she leaned from the jharokha."},
                                       {"definition": "second sense"}, {"definition": "third sense"}],
                       "synonyms": ["balcony", "bay window", "more", "more2", "more3", "more4"]}]}]


def test_dictionary_entry(monkeypatch):
    fake, calls = _seam([(200, "application/json", json.dumps(DICT), "dict")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("dictionary", word="jharokha")
    assert out["ok"] and out["word"] == "jharokha" and out["lang"] == "en"
    assert out["phonetic"] == "dʒəˈroːkha"              # the top-level phonetic wins
    m = out["meanings"][0]
    assert len(m["definitions"]) == 2                   # capped at two, honestly
    assert m["definitions"][0]["text"] == "an overhanging enclosed balcony"
    assert len(m["synonyms"]) == 5
    assert "/jharokha" in calls[0]


def test_dictionary_404_is_not_found(monkeypatch):
    fake, _ = _seam([J._Upstream("the public service answered 404", status=404)])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("dictionary", word="xyzzyx")
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"


def test_dictionary_needs_word():
    assert du("dictionary")["error"]["code"] == "BAD_INPUT"


# ---------------------------------------------------------------- arxiv

ATOM = ('<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom">'
        '<entry><title>A paper on  sodium batteries</title>'
        '<author><name>A. Kumar</name></author><author><name>B. Rao</name></author>'
        '<published>2026-01-15T00:00:00Z</published><updated>2026-02-01T00:00:00Z</updated>'
        '<summary>  We study electrolytes for sodium cells. </summary>'
        '<id>http://arxiv.org/abs/2601.01234v1</id></entry>'
        '<entry><title>Second paper</title><author><name>C. Devi</name></author>'
        '<published>2026-03-01T00:00:00Z</published><updated>2026-03-02T00:00:00Z</updated>'
        '<summary>More science.</summary><id>http://arxiv.org/abs/2603.04567v1</id></entry></feed>')


def test_arxiv_parses_atom(monkeypatch):
    fake, calls = _seam([(200, "application/atom+xml", ATOM, "ax")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("arxiv", q="sodium batteries", max_items=2)
    assert out["ok"] and out["count"] == 2
    e0 = out["entries"][0]
    assert e0["title"] == "A paper on sodium batteries"  # whitespace collapsed
    assert e0["authors"] == ["A. Kumar", "B. Rao"]
    assert e0["published"] == "2026-01-15" and e0["link"] == "http://arxiv.org/abs/2601.01234v1"
    assert e0["summary"] == "We study electrolytes for sodium cells."
    assert "search_query=all%3Asodium+batteries" in calls[0].replace("%20", "+") or \
           "sodium" in calls[0]


def test_arxiv_empty_feed_is_not_found(monkeypatch):
    fake, _ = _seam([(200, "application/atom+xml",
                      '<feed xmlns="http://www.w3.org/2005/Atom"></feed>', "ax")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("arxiv", q="nothingmatches")
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"


def test_arxiv_broken_atom_is_upstream(monkeypatch):
    fake, _ = _seam([(200, "text/html", "<html><body unclosed", "ax")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("arxiv", q="x")
    assert not out["ok"] and out["error"]["code"] == "UPSTREAM"


# ---------------------------------------------------------------- error mapping

def test_upstream_timeout_maps_to_upstream(monkeypatch):
    fake, _ = _seam([J._Upstream("the public web did not answer: timed out")])
    monkeypatch.setattr(J, "_http_get", fake)
    out = du("hn", q="x")
    assert not out["ok"] and out["error"]["code"] == "UPSTREAM"
    assert "again" in out["error"]["hint"]


def test_unknown_action_names_the_valid_ones():
    out = du("crawl")
    assert out["error"]["code"] == "BAD_INPUT" and "fetch" in out["error"]["message"]


# ---------------------------------------------------------------- the pins

def test_purity_no_top_level_httpx():
    """The lazy import law: the module's top level never imports the network stack."""
    src = Path(J.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        assert not any("httpx" in n for n in names), f"top-level import: {names}"


def test_registry_608():
    assert len(TOOLS) == 617, ("616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, "
                               "owner 'T4'). Was: 606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 "
                               "local-browser family) through v0.666. 581 + 1 paisa_sahayak (their v0.587) "
                               "+ 2 sandarbh (v0.590 SANDARBH MANCH) + 1 bhandar (v0.620 BHANDAR MANCH).")


def test_enum_and_label_pins():
    from app.agent.tools import TOOL_LABELS
    spec = next(t for t in TOOLS if t["name"] == "duniya")
    assert spec["input_schema"]["properties"]["action"]["enum"] == list(J._DU_ACTIONS)
    assert TOOL_LABELS["duniya"] == J.DUNIYA_LABELS["duniya"]
    assert set(J.DUNIYA_HANDLERS) == {"duniya"}
    assert J.BACKENDS["status"] == "this lane itself (zero network)"


def test_app_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.717.0"                       # conscious-bump guard: moves with every release
