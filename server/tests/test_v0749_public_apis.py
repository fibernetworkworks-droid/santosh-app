"""v0.749 SAB PUBLIC APIS (owner: "NOW CONSOLIDATE ALL PUBLIC APIS FIRST" after reading publicapis.dev).

Hoola's catalog was ONE list (github.com/public-apis/public-apis, 2,161 APIs, v0.47). publicapis.dev is a second,
newer MIT list (github.com/marcelscruz/public-apis, 2,021 entries, with AI and Podcasts categories). The catalog now
holds both, de-duplicated, with three promises held here:
1. nothing she had is lost - every old id still resolves (an upstream rename keeps the old id as an alias), so a
   saved key or a remembered recipe still finds its API;
2. a second-list API is added only when the first does not already have it (same name, or the same API-owned host);
3. every answer credits both sources."""
import gzip
import json

from app.publicapis import build as B
from app.publicapis import service as P


def test_the_catalog_holds_both_lists():
    rows = P.catalog()
    src = {r.get("src") for r in rows}
    assert len(rows) >= 3000 and src == {"public-apis", "publicapis.dev"}
    cats = {r["cat"] for r in rows}
    assert {"AI", "Podcasts", "Government", "Finance"} <= cats
    assert len({r["id"] for r in rows}) == len(rows)                                  # ids unique
    assert all(r["id"].startswith("dev-") for r in rows if r["src"] == "publicapis.dev")
    first = {B._key(r["name"]) for r in rows if r["src"] == "public-apis"}
    added = [B._key(r["name"]) for r in rows if r["src"] == "publicapis.dev"]
    assert not first & set(added) and len(added) == len(set(added))                  # an added API is never a repeat


def test_new_apis_are_found_and_both_sources_credited():
    r = P.find("konkan railway train position")
    assert r["results"][0]["name"] == "Konkan Railway Live Train Position"
    assert "public-apis/public-apis" in r["source"] and "publicapis.dev" in r["source"]
    assert any("Podcast" in x["name"] or "Podcast" in x["desc"] for x in P.find("podcast")["results"])
    assert P.find("gst hsn")["results"][0]["name"] == "India GST HSN & SAC"          # the old ones still rank


def test_merge_rules():
    base = [{"id": "a-one", "name": "Open Weather", "desc": "", "cat": "Weather", "auth": "none", "https": True,
             "cors": "no", "link": "https://openweather.example/docs", "host": "openweather.example"}]
    extra = B.parse_dev({"entries": [
        {"API": "open-weather", "Description": "same name", "Auth": "", "Cors": "no", "Link": "https://x.example", "Category": "Weather"},
        {"API": "Weather Two", "Description": "same own host", "Auth": "", "Cors": "no",
         "Link": "https://openweather.example/v2", "Category": "Weather"},
        {"API": "Repo Tool", "Description": "shared host is no proof", "Auth": "apiKey", "Cors": "no",
         "Link": "https://github.com/someone/tool", "Category": "Development"},
        {"API": "No Link", "Description": "", "Auth": "", "Cors": "", "Link": "", "Category": "AI"}]})
    out = B.merge(base, extra)
    assert [r["name"] for r in out] == ["Open Weather", "Repo Tool"]
    assert out[0]["src"] == "public-apis" and out[1]["src"] == "publicapis.dev" and out[1]["auth"] == "apiKey"
    assert extra[0]["auth"] == "none"                                                 # an empty Auth = no key


def test_an_upstream_rename_keeps_the_old_id():
    old = [{"id": "science-math-astro", "name": "Astro API", "desc": "", "cat": "Science & Math", "auth": "none",
            "https": True, "cors": "no", "link": "https://astro.example", "host": "astro.example", "src": "public-apis"},
           {"id": "weather-gone", "name": "Gone Weather", "desc": "", "cat": "Weather", "auth": "none", "https": True,
            "cors": "no", "link": "https://gone.example", "host": "gone.example", "src": "public-apis"}]
    fresh = [{"id": "personality-astro", "name": "Astro API", "desc": "", "cat": "Personality", "auth": "none",
              "https": True, "cors": "no", "link": "https://astro.example", "host": "astro.example"}]
    out = B.keep_old(fresh, old)
    assert [r["id"] for r in out] == ["personality-astro", "weather-gone"]           # dropped upstream = kept
    assert out[0]["aka"] == ["science-math-astro"]                                   # renamed = alias


def test_every_id_she_could_have_saved_still_resolves():
    """The shipped catalog carries the v0.47 ids: the one upstream moved (VedIntel AstroAPI, Science & Math ->
    Personality) answers by its old id."""
    by = P.by_id()
    assert by["science-math-vedintel-astroapi"]["id"] == "personality-vedintel-astroapi"
    for i in ("authentication-authorization-micro-user-service", "development-micro-db", "weather-micro-weather"):
        assert i in by
    raw = json.loads(gzip.decompress(B.OUT.read_bytes()))
    assert len(raw) == len(P.catalog())
