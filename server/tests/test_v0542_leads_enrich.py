"""v0.543.0 P2 ENRICHMENT - the pass over kept rows' OWN websites, tests against RECORDED site fixtures with
ZERO network: the fetch / robots / DNS / MX / model boundaries are faked at module level (enrich._get,
enrich._robots_ok, enrich._resolve_dns, enrich._resolve_mx, llm.cheap_brain/openai_create) while the extraction,
the grading ladder, the rank, the cap refusal, the store writes, the run card and the card guards run FOR REAL."""
import asyncio
import time

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)
from tests.test_api import client  # noqa: F401

from app.leads import enrich as E
from app.leads import service as S
from app.leads.models import ensure_tables


# ---------------------------------------------------------------- recorded site fixtures (the "recorded" sites)
HOME = """<html><head><title>Medplus Pharmacy - Pune</title></head><body>
<nav><a href="/">Home</a> <a href="/contact-us">Contact</a> <a href="/about.html">About</a>
<a href="https://www.linkedin.com/company/medplus">LinkedIn</a>
<a href="https://instagram.com/">instagram home</a>
<a href="https://www.facebook.com/medpluspharma?fref=tag">Facebook</a></nav>
<h1>Medplus Pharmacy</h1>
<p>Write to <a href="mailto:Info@MedPlus.in">us</a> or sales@medplus.in. Our Rahul: rahul.sharma@medplus.in.
Personal: rahul@gmail.com</p>
<img src="logo.png"><p>noreply@medplus.in sentry@medplus.in hidden@script.in</p>
<script>var leak = "leaked@scriptjs.in";</script>
</body></html>"""

CONTACT = """<html><head><title>Contact Us</title></head><body>
<h1>Contact</h1><p>email contact@medplus.in, phone +91 98765 11111</p>
<a href="https://twitter.com/medplus">Twitter</a>
</body></html>"""

CHALLENGE = """<html><head><title>Just a moment...</title></head>
<body><script>window._pxAppId="PX1234";</script><p>Checking your browser</p></body></html>"""


class _Page:
    """The duck-typed scrapling page enrich._get hands back (html_content / status / url)."""

    def __init__(self, url: str, html: str, status: int = 200):
        self.url, self.html_content, self.status = url, html, status


def fake_site(monkeypatch, pages_by_url, robots=True):
    """The network boundary: enrich._get answers from the recorded fixture dict, robots is a word."""
    monkeypatch.setattr(E, "_robots_ok", lambda u: robots)
    monkeypatch.setattr(E, "HOST_MIN_INTERVAL", 0.0)

    def fake_get(url, tenant_id, **k):
        hit = pages_by_url.get(url) or pages_by_url.get(url.rstrip("/"))
        if hit is None:
            raise ConnectionError(f"fixture site {url} not reachable (recorded world has it dead)")
        html, status = hit if isinstance(hit, tuple) else (hit, 200)
        return _Page(url, html, status)

    monkeypatch.setattr(E, "_get", fake_get)


def fake_dns(monkeypatch, alive=("medplus.in",), mx=("medplus.in",)):
    monkeypatch.setattr(E, "_resolve_dns", lambda d: d in alive)
    monkeypatch.setattr(E, "_resolve_mx", lambda d: d in mx)


# ================================================================ the read (pure string work)
def test_extract_emails_reads_mailto_and_pruned_text_and_skips_junk():
    got = E.extract_emails(HOME)
    assert "info@medplus.in" in got and "sales@medplus.in" in got and "rahul.sharma@medplus.in" in got
    assert "rahul@gmail.com" in got                      # a personal address is still a candidate - the rank decides
    assert "hidden@script.in" in got                     # visible page text (odd, but it IS on the page)
    assert "leaked@scriptjs.in" not in got               # inside <script> = code, not a contact
    assert "noreply@medplus.in" not in got and "sentry@medplus.in" not in got
    assert all("@" in e for e in got)


def test_extract_socials_by_hostname_platform_homes_are_not_handles():
    got = E.extract_socials(HOME, "https://medplus.in")
    assert got.get("linkedin") == "https://www.linkedin.com/company/medplus"
    assert got.get("facebook") == "https://www.facebook.com/medpluspharma"
    assert "instagram" not in got                        # the instagram HOME page is not the business's handle


def test_contact_links_pick_the_pages_worth_one_more_fetch():
    got = E.contact_links(HOME, "https://medplus.in")
    assert "https://medplus.in/contact-us" in got and "https://medplus.in/about.html" in got
    assert len(got) <= E.SITE_PAGES_MAX


def test_site_pass_reads_home_then_contact_and_bounds_the_pages(monkeypatch):
    fake_site(monkeypatch, {"https://medplus.in": HOME, "https://medplus.in/contact-us": CONTACT,
                            "https://medplus.in/about.html": CONTACT})
    out = E.site_pass("https://medplus.in", "t1")
    urls = [p["url"] for p in out["pages"]]
    assert urls[0] == "https://medplus.in" and "https://medplus.in/contact-us" in urls
    assert len(urls) == E.SITE_PAGES_MAX                  # home + contact-ish pages, the site bound holds
    assert "contact@medplus.in" in out["emails"] and "info@medplus.in" in out["emails"]
    assert out["socials"]["twitter"] == "https://twitter.com/medplus"
    assert out["blocked"] == [] and out["parser_version"].startswith("v0.684")


def test_site_pass_names_the_block_and_the_dead_site_never_crashes(monkeypatch):
    fake_site(monkeypatch, {"https://shop.in": CHALLENGE, "https://dead.in": None})
    out = E.site_pass("https://shop.in", "t1")
    assert out["blocked"] and "challenge" in out["blocked"][0] and out["emails"] == []
    out2 = E.site_pass("https://dead.in", "t1")           # _get raised - a RESULT, not an exception
    assert out2["pages"][0]["dead"] and out2["emails"] == []


def test_politeness_sleeps_between_same_host_fetches(monkeypatch):
    monkeypatch.setattr(E, "HOST_MIN_INTERVAL", 0.05)
    E._LAST_HIT.clear()
    t0 = time.monotonic()
    E._polite("medplus.in")
    E._polite("medplus.in")
    assert time.monotonic() - t0 >= 0.04                  # the second same-host hit waited its turn
    E._LAST_HIT.clear()


# ================================================================ the grade (DNS -> MX -> disposable)
def test_grade_email_ladder(monkeypatch):
    fake_dns(monkeypatch, alive=("medplus.in", "nomx.in"), mx=("medplus.in",))
    assert E.grade_email("info@medplus.in") == "pakka"    # DNS + MX + not disposable
    assert E.grade_email("info@nomx.in") == "sadak_tak"   # DNS alive, no MX - mail may not flow
    fake_dns(monkeypatch, alive=(), mx=())
    assert E.grade_email("info@medplus.in") == "galat"    # dead domain
    assert E.grade_email("x@mailinator.com") == "galat"   # disposable, no DNS needed
    assert E.grade_email("bogus-at-all") == "galat"       # syntax dead, no network touched


def test_rank_emails_role_over_named_over_personal():
    got = E.rank_emails(["rahul@gmail.com", "info@medplus.in", "rahul.sharma@medplus.in"], "Medplus Pharmacy")
    assert got[0] == "info@medplus.in"                    # role inbox first...
    assert got[1] == "rahul.sharma@medplus.in"            # ...named person second, personal domain last
    named = E.rank_emails(["info@x.in", "deepa.patil@sunriseclinic.in"], "Sunrise Clinic")
    assert named[0] == "deepa.patil@sunriseclinic.in"     # a name that matches the business lifts it


def test_best_email_single_candidate_needs_no_model():
    out = asyncio.run(E.best_email(["only@medplus.in"], "Medplus"))
    assert out == {"email": "only@medplus.in", "reason": "ek hi candidate mila", "pick": "single"}


def test_best_email_ai_pick_is_validated_and_falls_back_to_rule(monkeypatch):
    import app.agent.llm as llm

    async def fake_create(brain, system, tools, msgs, max_tokens):
        text = msgs[0]["content"][0]["text"]
        assert "info@medplus.in" in text                  # the candidates went to the model
        blocks = [{"type": "text", "text": '{"email": "rahul.sharma@medplus.in", "reason": "naam match"}'}]
        return blocks, "", {"prompt_tokens": 100, "completion_tokens": 20}

    monkeypatch.setattr(llm, "cheap_brain", lambda: "glm-4-flash")
    monkeypatch.setattr(llm, "openai_create", fake_create)
    out = asyncio.run(E.best_email(["info@medplus.in", "rahul.sharma@medplus.in"], "Medplus Pharmacy"))
    assert out["pick"] == "ai" and out["email"] == "rahul.sharma@medplus.in" and out["reason"]

    async def dead_create(*a, **k):
        raise RuntimeError("model down")
    monkeypatch.setattr(llm, "openai_create", dead_create)
    out2 = asyncio.run(E.best_email(["info@medplus.in", "rahul.sharma@medplus.in"], "Medplus Pharmacy"))
    assert out2["pick"] == "rule" and out2["email"] == "info@medplus.in"   # the honest fallback, labelled


def test_best_email_rejects_a_hallucinated_pick(monkeypatch):
    import app.agent.llm as llm

    async def lying_create(brain, system, tools, msgs, max_tokens):
        return [{"type": "text", "text": '{"email": "ceo@not-in-the-list.in", "reason": "banaya hua"}'}], "", {}

    monkeypatch.setattr(llm, "cheap_brain", lambda: "glm-4-flash")
    monkeypatch.setattr(llm, "openai_create", lying_create)
    out = asyncio.run(E.best_email(["info@medplus.in", "sales@medplus.in"], "Medplus"))
    assert out["pick"] == "rule" and out["email"] == "info@medplus.in"     # a made-up pick never ships


# ================================================================ the orchestrator (store + cap + run card)
def _row(name, website, email="", lane="OFFICIAL_API"):
    return S.add_row("t1", {"name": name, "place_id": f"PID_{name}", "city": "Pune",
                            "website": website, "email": email}, lane, f"https://maps.google.com/?cid={name}")


def test_enrich_fills_the_empty_slot_and_grades(env, monkeypatch):
    fake_site(monkeypatch, {"https://medplus.in": HOME, "https://medplus.in/contact-us": CONTACT})
    fake_dns(monkeypatch)
    row = _row("Medplus", "https://medplus.in")
    out = asyncio.run(S.enrich("t1", use_model=False))
    assert out["ok"] is True and out["run"]["status"] == "DONE"
    assert out["enriched"] == 1 and out["picks"]["rule"] == 1
    r = S.rows("t1")["rows"][0]
    assert r["id"] == row["id"]
    assert r["email"] in ("info@medplus.in", "contact@medplus.in")   # the rule rank's deterministic tie-break
    assert r["email_grade"] == "pakka"
    assert r["socials"]["linkedin"].endswith("/company/medplus")
    assert r["enriched_from"] == "https://medplus.in" and r["enrich_note"].startswith("rule")
    assert r["enriched_at"]
    assert out["run"]["lanes"] == []                      # enrichment is NOT a source lane
    assert out["run"]["plan"]["kind"] == "enrich" and out["run"]["found"] == 1 and out["run"]["kept"] == 1
    assert out["run"]["bill"]["model_calls"] == 0 and "sites_read" in out["run"]["bill"]


def test_enrich_never_overwrites_an_email_but_regrades_it(env, monkeypatch):
    fake_site(monkeypatch, {"https://other.in": HOME})
    fake_dns(monkeypatch, alive=("other.in", "elsewhere.in"), mx=("other.in", "elsewhere.in"))
    _row("Medplus", "https://other.in", email="kept@elsewhere.in")
    out = asyncio.run(S.enrich("t1", use_model=False))
    r = S.rows("t1")["rows"][0]
    assert r["email"] == "kept@elsewhere.in"              # another source's email stays
    assert r["email_grade"] == "pakka" and r["enriched_at"] and r["enriched_from"] == "https://other.in"


def test_enrich_dead_site_is_galat_not_a_crash(env, monkeypatch):
    fake_site(monkeypatch, {"https://medplus.in": None})  # the recorded world: this site is dead
    fake_dns(monkeypatch)
    _row("Medplus", "https://medplus.in", email="front@medplus.in")
    out = asyncio.run(S.enrich("t1", use_model=False))
    assert out["ok"] is True and out["dead_site"] == 1
    r = S.rows("t1")["rows"][0]
    assert r["email"] == "front@medplus.in" and r["email_grade"] == "galat"
    assert "site dead" in r["enrich_note"]
    assert out["run"]["refused"] == 1                     # the honest counter, not a pretend-complete pass


def test_enrich_dead_site_of_another_domain_leaves_the_grade(env, monkeypatch):
    fake_site(monkeypatch, {"https://shopfront.in": None})
    fake_dns(monkeypatch)
    _row("Medplus", "https://shopfront.in", email="front@medplus.in")
    out = asyncio.run(S.enrich("t1", use_model=False))
    r = S.rows("t1")["rows"][0]
    assert r["email_grade"] == ""                         # a dead shopfront says nothing about another domain's mail


def test_enrich_blocked_site_is_recorded(env, monkeypatch):
    fake_site(monkeypatch, {"https://shop.in": CHALLENGE})
    fake_dns(monkeypatch)
    _row("Shop", "https://shop.in")
    out = asyncio.run(S.enrich("t1", use_model=False))
    r = S.rows("t1")["rows"][0]
    assert out["blocked"] == 1 and r["enrich_note"].startswith("blocked:") and r["email"] == ""


def test_enrich_cap_refuses_at_plan_time(env, monkeypatch):
    fake_site(monkeypatch, {})
    fake_dns(monkeypatch)
    for i in range(3):
        _row(f"Shop{i}", f"https://shop{i}.in")
    monkeypatch.setattr(env["settings"], "leads_enrich_rows_per_run", 2)
    with pytest.raises(S.LeadsError, match=r"\b2\b"):
        asyncio.run(S.enrich("t1", use_model=False))
    assert S.rows("t1")["rows"][0]["email"] == ""         # nothing moved - a refusal is a refusal


def test_enrich_targets_have_websites_and_honour_opt_out(env, monkeypatch):
    fake_site(monkeypatch, {"https://medplus.in": HOME})
    fake_dns(monkeypatch)
    _row("Medplus", "https://medplus.in")
    no_site = S.add_row("t1", {"name": "NoSite", "place_id": "PID_NS", "city": "Pune"}, "OFFICIAL_API", "s://x")
    gone = _row("Gone", "https://medplus.in")
    S.set_opt_out("t1", gone["id"], True)
    out = asyncio.run(S.enrich("t1", use_model=False))
    assert out["run"]["found"] == 1                       # the no-website and the opted-out row were never targets
    assert all(d["name"] != "NoSite" for d in out["details"])


def test_enrich_picks_single_and_counts_no_email(env, monkeypatch):
    fake_site(monkeypatch, {"https://one.in": "<html><body><p>hi@one.in</p></body></html>",
                            "https://empty.in": "<html><body><p>Call us on the phone.</p></body></html>"})
    fake_dns(monkeypatch, alive=("one.in",), mx=("one.in",))
    _row("One", "https://one.in")
    _row("Empty", "https://empty.in")
    out = asyncio.run(S.enrich("t1", use_model=False))
    assert out["picks"].get("single", 0) == 0             # the deterministic path counts rule, not single
    assert out["picks"]["rule"] == 1 and out["no_email"] == 1
    rows = {r["name"]: r for r in S.rows("t1")["rows"]}
    assert rows["One"]["email"] == "hi@one.in" and rows["One"]["email_grade"] == "pakka"
    assert rows["Empty"]["email"] == "" and rows["Empty"]["enriched_at"]   # read, recorded, nothing filled


def test_enrich_model_pick_goes_on_the_bill(env, monkeypatch):
    fake_site(monkeypatch, {"https://medplus.in": HOME})
    fake_dns(monkeypatch)
    import app.agent.llm as llm

    async def fake_create(brain, system, tools, msgs, max_tokens):
        from app import usage as _u
        _u.from_openai("glm-4-flash", {"prompt_tokens": 150, "completion_tokens": 30})   # the real boundary records
        return [{"type": "text",
                 "text": '{"email": "sales@medplus.in", "reason": "sales desk sambhalta hai"}'}], "", \
            {"prompt_tokens": 150, "completion_tokens": 30}

    monkeypatch.setattr(llm, "cheap_brain", lambda: "glm-4-flash")
    monkeypatch.setattr(llm, "openai_create", fake_create)
    _row("Medplus", "https://medplus.in")
    out = asyncio.run(S.enrich("t1", use_model=True))
    assert out["picks"]["ai"] == 1 and out["run"]["bill"]["model_calls"] == 1
    assert out["run"]["bill"]["tok_in"] == 150 and out["run"]["bill"]["tok_out"] == 30
    assert out["run"]["bill"]["inr"] >= 0.0
    r = S.rows("t1")["rows"][0]
    assert r["email"] == "sales@medplus.in" and r["enrich_note"].startswith("ai:")


# ================================================================ the surface (tool + API + card)
def test_leads_enrich_tool_runs_the_pass(env, monkeypatch):
    from app.agent.leads_tools import LEADS_HANDLERS

    class _C:                                    # the duck-typed Ctx the handler reads
        tenant_id, conversation_id, actor = "t1", "c1", "owner"

    _row("Medplus", "https://medplus.in")
    fake_site(monkeypatch, {"https://medplus.in": HOME})
    fake_dns(monkeypatch)
    out = asyncio.run(LEADS_HANDLERS["leads_enrich"](_C(), use_model=False))
    assert out["ok"] is True and out["run"]["plan"]["kind"] == "enrich"
    assert S.rows("t1")["rows"][0]["email"] in ("info@medplus.in", "contact@medplus.in")


def test_enrich_through_the_api(env, monkeypatch):
    # the API's tenant is the client fixture's own - add the row as THAT tenant
    S.add_row("default", {"name": "Medplus", "place_id": "PID_API", "city": "Pune",
                          "website": "https://medplus.in"}, "OFFICIAL_API", "https://maps.google.com/?cid=API")
    fake_site(monkeypatch, {"https://medplus.in": HOME})
    fake_dns(monkeypatch)
    with client(monkeypatch, env, api_key="secret") as c:
        h = {"Authorization": "Bearer secret"}
        r = c.post("/api/leads/enrich", headers=h, json={"use_model": False})
        assert r.status_code == 200 and r.json()["run"]["plan"]["kind"] == "enrich"
        got = c.get("/api/leads/rows", headers=h).json()["rows"][0]
        assert got["email"] in ("info@medplus.in", "contact@medplus.in")
        # the cap refusal comes back as a 400 with the cap named, not a 500
        monkeypatch.setattr(env["settings"], "leads_enrich_rows_per_run", 1)
        S.add_row("default", {"name": "Two", "place_id": "PID_TWO", "city": "Pune",
                              "website": "https://two.in"}, "OFFICIAL_API", "https://maps.google.com/?cid=TWO")
        bad = c.post("/api/leads/enrich", headers=h, json={"use_model": False})
        assert bad.status_code == 400 and "cap" in bad.json()["detail"].lower()


def test_card_guards_carry_the_enrich_walls(env):
    from app.quality import leadscard
    card = leadscard.free_card()
    g = card["guards"]
    for k in ("enrich_built", "enrich_uses_existing_stack", "no_smtp_probe", "email_grade_vocab",
              "enrich_cap_named", "cap_refuses"):
        assert g[k] is True, f"guard {k} = {g[k]}"
    assert card["set"] == 6 and card["guards_ok"] == len(g)   # v0.684.0: set v6 - the outreach handoff walls joined


def test_no_smtp_probe_in_the_source():
    import inspect
    src = inspect.getsource(E)
    assert "smtplib" not in src.lower() and "aiosmtplib" not in src.lower()
