"""v0.684.0 KALA MANCH - the T5 knowledge-skill catalog family, backend-only (owner: "GO" on the
google/skills deploy plan; upstream github.com/google/skills, Apache-2.0, fork-and-remix
sanctioned; IDEA-ONLY: zero upstream code - what ported is the finding-google-skills meta-skill's
byte-exact catalog fetch, the routing rule's predictable-families + never-infer laws, the SKILL.md
anatomy's progressive disclosure, and the attribution tag law).

ONE tool `kala`, actions catalog | read | references | list | status, every answer one envelope.
What is tested FOR REAL - the whole suite is OFFLINE (zero network): every public byte rides the
ONE seam `kala_tools._http_get`, every test monkeypatches exactly that, and an autouse fixture
keeps the catalog cache cold between tests:

the envelope shape (ok / error{code, message, hint} / meta{elapsed_ms, backend}), status (zero
network, upstream + cache + caps + laws + the sibling pointers, the cache block honest when cold),
the kill switch (off means off - every action NEED_SETUP), catalog (the fixture catalog narrowed
by a case-insensitive regex over name+description, the cap with the honest note, the no-query
alphabetical bias note, a broken regex degrading to a literal find, the cache really caching -
the second call touches no seam - and the TTL expiry really refetching, a bad-JSON answer =
UPSTREAM with the failure recorded for status), read (the byte-exact SKILL.md body + the
description riding along, an unknown name = NOT_FOUND with the never-guess hint, the honest
truncation note at the 12k cap, TOO_BIG past the download cap, the PAN id-mask riding the text),
references (the url derived from the entrypoint and still allowlisted, a 404 = NOT_FOUND honesty,
a traversal file name refused before any network, a non-SKILL.md entrypoint refused), list (a
known prefix hits, an unknown prefix empty with the family table, an empty prefix listed as no
items + the note), the allowlist itself (http:// refused, the non-raw github.com host refused, a
foreign host refused, a wrong path shape refused - all by name, NOT_ALLOWED), the SSRF guard
itself wired into the lane (loopback = BLOCKED through the real house guard), error mapping (an
upstream timeout = UPSTREAM), an unknown action naming the valid ones, the attribution tag (the
UA carries hoola-kala and the idea-only mark), the purity pin (no top-level httpx - the lazy
import law), registry 609 pin, the enum pin, APP_VERSION pin.
"""
import asyncio
import ast
import json
from pathlib import Path

import pytest

from app.agent import kala_tools as K
from app.agent.tools import Ctx, TOOLS

CTX = Ctx(tenant_id="kala-test-tenant", conversation_id="c1")

RAW = "https://raw.githubusercontent.com/google/skills/main"

CATALOG = {"generator": "This file is generated. Do not edit it by hand.", "skills": [
    {"name": "gemini-api",
     "description": "Use when the user asks about Gemini in an enterprise environment or mentions "
                    "Vertex AI. Guides the Gemini API on Agent Platform with the Gen AI SDK. "
                    "Invoice no ABCPF1234F rides inside for the mask test.",
     "entrypoint": f"{RAW}/skills/cloud/gemini-api/SKILL.md"},
    {"name": "gke-basics",
     "description": "GKE Basics & Critical Gotchas - clusters, nodes, networking. Use when creating "
                    "or debugging a GKE cluster.",
     "entrypoint": f"{RAW}/skills/cloud/gke-basics/SKILL.md"},
    {"name": "google-cloud-waf-security",
     "description": "Google Cloud Well-Architected Framework skill for the Security pillar.",
     "entrypoint": f"{RAW}/skills/cloud/google-cloud-waf-security/SKILL.md"},
    {"name": "google-ads-api-quickstart",
     "description": "Google Ads API Quickstart - generate the five credentials.",
     "entrypoint": f"{RAW}/skills/ads/google-ads-api-quickstart/SKILL.md"},
]}


def _catalog_body():
    return json.dumps(CATALOG)


def kl(action="status", ctx=None, **kw):
    return asyncio.run(K.kala(ctx or CTX, action, **kw))


def _seam(responses):
    """A fake seam: pops one (status, ctype, text, final_url) per call, records the urls."""
    calls = []

    async def fake(url):
        calls.append(url)
        item = responses.pop(0) if responses else (200, "text/plain", "{}", url)
        if isinstance(item, Exception):
            raise item
        return item

    return fake, calls


@pytest.fixture(autouse=True)
def _cold_cache():
    """Every test starts with a cold catalog cache - no test depends on another's fetch."""
    K._cache_reset()
    yield
    K._cache_reset()


# ---------------------------------------------------------------- the shape

def test_envelope_shape_always():
    for out in (kl("status"), kl("nope"), kl("read", name="nope"),
                kl("catalog"), kl("list", prefix="gke-")):
        assert out["schema_version"] == 1 and out["tool"] == "kala"
        assert set(out) >= {"ok", "action", "error", "meta"}
        assert isinstance(out["meta"]["elapsed_ms"], int)
        assert out["meta"]["backend"]
        assert out["error"] is None or set(out["error"]) == {"code", "message", "hint"}


def test_status_is_zero_network():
    fake, calls = _seam([])
    real, K._http_get = K._http_get, fake
    try:
        out = kl("status")
    finally:
        K._http_get = real
    assert out["ok"] and calls == []                    # status never touches the seam
    assert out["actions"] == list(K._KL_ACTIONS)
    assert out["upstream"]["host_allowlist"] == "raw.githubusercontent.com"
    assert "index.json" in out["upstream"]["index"]
    assert out["cache"]["entries"] == 0 and out["cache"]["age_s"] is None
    assert out["caps"]["skill_chars"] == K._MAX_SKILL_CHARS
    assert any("GET only" in law for law in out["laws"])
    assert any("never" in law and "execut" in law for law in out["laws"])
    assert "duniya" in out["siblings"] and "jharokha" in out["siblings"]


def test_kill_switch_off_means_off(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "kala_enabled", False, raising=False)
    out = kl("catalog", q="gke")
    assert not out["ok"] and out["error"]["code"] == "NEED_SETUP"
    assert "kala_enabled=true" in out["error"]["hint"]


# ---------------------------------------------------------------- catalog

def test_catalog_narrows_by_regex(monkeypatch):
    fake, calls = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("catalog", q=r"gke.*gotchas|waf")
    assert out["ok"] and out["catalog_size"] == 4
    assert out["total_matches"] == 2 and out["count"] == 2
    names = {i["name"] for i in out["items"]}
    assert names == {"gke-basics", "google-cloud-waf-security"}
    assert all(i["entrypoint"].startswith(RAW + "/skills/") for i in out["items"])
    assert len(calls) == 1 and calls[0].endswith("/index.json")


def test_catalog_is_case_insensitive_and_masks_descriptions(monkeypatch):
    fake, _ = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("catalog", q="VERTEX AI")
    assert out["ok"] and out["total_matches"] == 1 and out["items"][0]["name"] == "gemini-api"
    assert "ABCXXXXXXF" in out["items"][0]["description"]      # the PAN id-mask rode the text
    assert "ABCPF1234F" not in out["items"][0]["description"]


def test_catalog_cap_is_honest(monkeypatch):
    many = {"skills": [{"name": f"skill-{i:03d}", "description": f"desc {i}",
                        "entrypoint": f"{RAW}/skills/cloud/skill-{i:03d}/SKILL.md"}
                       for i in range(40)]}
    fake, _ = _seam([(200, "text/plain", json.dumps(many), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("catalog", q="desc")
    assert out["ok"] and out["total_matches"] == 40 and out["count"] == K._MAX_CATALOG_HITS
    assert "narrow the query" in out["note"]


def test_catalog_no_query_warns_the_alphabetical_bias(monkeypatch):
    fake, _ = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("catalog")
    assert out["ok"] and out["count"] == 4 and out["query"] is None
    assert "alphabetical" in out["note"] and "narrow" in out["note"]


def test_catalog_broken_regex_degrades_to_literal(monkeypatch):
    fake, _ = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("catalog", q="gke-(")                      # an invalid regex on purpose
    assert out["ok"] and out["total_matches"] == 0      # the literal 'gke-(' matches nothing - no crash


def test_catalog_cache_really_caches(monkeypatch):
    fake, calls = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    first = kl("catalog", q="gke")
    second = kl("catalog", q="gemini")
    assert first["ok"] and second["ok"]
    assert len(calls) == 1                              # the second ask rode the cache - no second fetch
    assert second["catalog_size"] == 4


def test_catalog_ttl_expiry_refetches(monkeypatch):
    fake, calls = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json"),
                         (200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    monkeypatch.setattr(K, "_ttl", lambda: 0)           # every fetch is already stale
    kl("catalog", q="gke")
    kl("list", prefix="gemini-")
    assert len(calls) == 2                              # the TTL of zero forced the refetch


def test_catalog_bad_json_is_upstream_and_told(monkeypatch):
    fake, _ = _seam([(200, "text/plain", "<html>not json</html>", RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("catalog")
    assert not out["ok"] and out["error"]["code"] == "UPSTREAM"
    assert "not JSON" in out["error"]["message"]
    st = kl("status")                                   # status tells the failure honestly
    assert st["ok"] and st["cache"]["last_ok"] is False and "not JSON" in st["cache"]["last_error"]


# ---------------------------------------------------------------- read

def test_read_fetches_the_document(monkeypatch):
    body = ("---\nname: gemini-api\n---\n# Gemini API in Agent Platform\n\nALWAYS use the Gen AI SDK. "
            "An invoice ABCPF1234F rides inside for the mask test.")
    fake, calls = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json"),
                         (200, "text/plain; charset=utf-8", body, f"{RAW}/skills/cloud/gemini-api/SKILL.md")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("read", name="gemini-api")
    assert out["ok"] and out["name"] == "gemini-api"
    assert "Gen AI SDK" in out["text"]
    assert "ABCXXXXXXF" in out["text"] and "ABCPF1234F" not in out["text"]
    assert out["description"].startswith("Use when")
    assert calls[0].endswith("/index.json") and calls[1].endswith("/skills/cloud/gemini-api/SKILL.md")


def test_read_unknown_name_is_never_guessed(monkeypatch):
    fake, _ = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("read", name="gke-cluster-creation")       # a plausible name that is NOT in the fixture
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"
    assert "never infer" in out["error"]["message"] or "catalog" in out["error"]["message"]
    assert "action=catalog" in out["error"]["hint"]


def test_read_truncates_honestly(monkeypatch):
    body = "# big\n\n" + ("word " * 4_000)              # ~20k chars > the 12k cap
    fake, _ = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json"),
                     (200, "text/plain", body, f"{RAW}/skills/cloud/gke-basics/SKILL.md")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("read", name="gke-basics")
    assert out["ok"] and out["chars"] == K._MAX_SKILL_CHARS
    assert "truncated" in out["note"]


def test_read_too_big_is_honest(monkeypatch):
    fake, _ = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json"),
                     (200, "text/plain", "x" * (K._MAX_BODY_CHARS + 1), f"{RAW}/skills/cloud/gke-basics/SKILL.md")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("read", name="gke-basics")
    assert not out["ok"] and out["error"]["code"] == "TOO_BIG"


def test_read_empty_name_is_bad_input():
    out = kl("read", name="")
    assert not out["ok"] and out["error"]["code"] == "BAD_INPUT"
    assert "name" in out["error"]["message"]


# ---------------------------------------------------------------- references

def test_references_derives_and_fetches(monkeypatch):
    body = "# Usage Attribution\n\nTag every gcloud command with the attribution env var."
    fake, calls = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json"),
                         (200, "text/plain", body, f"{RAW}/skills/cloud/gemini-api/references/attribution.md")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("references", name="gemini-api", file="attribution.md")
    assert out["ok"] and out["file"] == "attribution.md"
    assert "attribution env var" in out["text"]
    assert calls[1].endswith("/skills/cloud/gemini-api/references/attribution.md")


def test_references_404_is_not_found(monkeypatch):
    fake, _ = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json"),
                     K._Upstream("the upstream answered 404", status=404)])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("references", name="gemini-api", file="missing.md")
    assert not out["ok"] and out["error"]["code"] == "NOT_FOUND"


def test_references_traversal_refused_before_the_network(monkeypatch):
    fake, calls = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("references", name="gemini-api", file="../evil.md")
    assert not out["ok"] and out["error"]["code"] == "BAD_INPUT"
    assert calls == []                                  # refused before ANY fetch - not even the catalog


def test_references_non_skillmd_entrypoint_refused(monkeypatch):
    odd = {"skills": [{"name": "odd-one", "description": "d",
                       "entrypoint": f"{RAW}/skills/cloud/odd-one/OTHER.md"}]}
    fake, _ = _seam([(200, "text/plain", json.dumps(odd), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("references", name="odd-one", file="a.md")
    assert not out["ok"] and out["error"]["code"] == "UPSTREAM"
    assert "SKILL.md" in out["error"]["message"]


# ---------------------------------------------------------------- list

def test_list_known_prefix(monkeypatch):
    fake, _ = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("list", prefix="google-cloud-waf-")
    assert out["ok"] and out["count"] == 1 and out["items"][0]["name"] == "google-cloud-waf-security"
    assert out["families"]["gke-"].startswith("GKE")


def test_list_unknown_prefix_empty_with_families(monkeypatch):
    fake, _ = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("list", prefix="azure-")
    assert out["ok"] and out["count"] == 0 and out["items"] == []
    assert "families" in out and "never infer" in out["note"]


def test_list_empty_prefix_lists_nothing_but_the_families(monkeypatch):
    fake, _ = _seam([(200, "text/plain", _catalog_body(), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("list")
    assert out["ok"] and out["items"] == [] and out["prefix"] is None
    assert "pick a family" in out["note"] and len(out["families"]) >= 10


# ---------------------------------------------------------------- the allowlist (the second wall)

def test_allowlist_refuses_by_name():
    for url in ("http://raw.githubusercontent.com/google/skills/main/index.json",        # not https
                "https://github.com/google/skills/main/index.json",                      # not the raw host
                "https://raw.githubusercontent.com/google/skills/main/index.json.bak",   # wrong path
                "https://raw.githubusercontent.com/evil/skills/main/index.json",         # wrong repo
                "https://raw.githubusercontent.com/google/skills/main/skills/A/B/SKILL.md",  # bad shape
                "https://example.com/index.json"):                                       # foreign host
        with pytest.raises(K._NotAllowed):
            K._whitelist(url)


def test_allowlist_accepts_the_house_paths():
    for url in (RAW + "/index.json",
                RAW + "/skills/cloud/gke-basics/SKILL.md",
                RAW + "/skills/ads/google-ads-api-quickstart/references/attribution.md"):
        assert K._whitelist(url) == url


def test_allowlist_rides_every_fetch_path(monkeypatch):
    """The whitelist is the lane's own wall - a catalog entry's url is re-validated even though
    the catalog itself came from the allowlisted host."""
    evil = {"skills": [{"name": "gemini-api", "description": "d",
                        "entrypoint": "https://example.com/evil.md"}]}
    fake, calls = _seam([(200, "text/plain", json.dumps(evil), RAW + "/index.json")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("read", name="gemini-api")
    assert not out["ok"] and out["error"]["code"] == "NOT_ALLOWED"
    assert "allowlist" in out["error"]["message"] and calls == [f"{RAW}/index.json"]


def test_ssrf_loopback_blocked_through_the_real_guard():
    """The house guard is the FIRST wall (literal loopback url, zero DNS): a private address never
    reaches the seam even if a catalog entry or a query tried to smuggle one in."""
    from app.agent.scrape_tools import ToolError
    with pytest.raises(ToolError):
        K._guard_url("http://127.0.0.1/google/skills/main/index.json")
    with pytest.raises(ToolError):
        K._guard_url("file:///etc/passwd")


# ---------------------------------------------------------------- error mapping

def test_upstream_timeout_maps_to_upstream(monkeypatch):
    fake, _ = _seam([K._Upstream("the upstream did not answer: timed out")])
    monkeypatch.setattr(K, "_http_get", fake)
    monkeypatch.setattr(K, "_guard_url", lambda u: u)
    out = kl("catalog")
    assert not out["ok"] and out["error"]["code"] == "UPSTREAM"
    assert "again" in out["error"]["hint"]


def test_unknown_action_names_the_valid_ones():
    out = kl("install")                                 # the routing rule's other path - never this lane's
    assert out["error"]["code"] == "BAD_INPUT" and "catalog" in out["error"]["message"]


def test_attribution_tag_law():
    assert K._UA.startswith("hoola-kala/")
    assert "google-skills catalog" in K._UA and "idea-only" in K._UA
    assert "Apache-2.0" in K._UA                        # the license rides the tag too


# ---------------------------------------------------------------- the pins

def test_purity_no_top_level_httpx():
    """The lazy import law: the module's top level never imports the network stack."""
    src = Path(K.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        assert not any("httpx" in n for n in names), f"top-level import: {names}"


def test_registry_609():
    assert len(TOOLS) == 627, ("626 + 1 app_engine (v0.824 APP ENGINE 1: the Web Studio React app lane - one new tool). " "617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, "
                               "owner 'GO' on the google/skills deploy plan). Was: 607 + 1 duniya "
                               "(v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). "
                               "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). "
                               "581 + 1 paisa_sahayak (their v0.587) + 2 sandarbh (v0.590 SANDARBH MANCH) "
                               "+ 1 bhandar (v0.620 BHANDAR MANCH).")


def test_enum_and_label_pins():
    from app.agent.tools import TOOL_LABELS
    spec = next(t for t in TOOLS if t["name"] == "kala")
    assert spec["input_schema"]["properties"]["action"]["enum"] == list(K._KL_ACTIONS)
    assert TOOL_LABELS["kala"] == K.KALA_LABELS["kala"]
    assert set(K.KALA_HANDLERS) == {"kala"}
    assert K.BACKENDS["status"] == "this lane itself (zero network)"
    assert K._CACHE["data"] is None                     # the autouse fixture left it cold


def test_app_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.825.0"                       # conscious-bump guard: moves with every release
