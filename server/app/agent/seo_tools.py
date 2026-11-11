"""v0.103 SEO Sahayak tools. `seo_dekho` only reads; `seo` does the work. Hoola never publishes to her website or Google
profile: drafts become final on HER Haan and she puts them up. Official Google APIs only (Search Console, PageSpeed);
no scraping of Google results, no link buying, no fake reviews."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

SEO_TOOLS = [
    {"name": "seo", "description": (
        "SEO specialist for HER website (or her client's) and Google Business Profile, end to end. action=site: url, name, "
        "city, state, street, pin, phone, schema_type (LocalBusiness / Dentist / Restaurant / Store...), hours (e.g. Mo-Sa "
        "10:00-20:00), services [what she sells], site (to update). action=audit: site, max_pages -> crawls her site (robots.txt "
        "honoured), checks every page + site, makes the fix list with the exact fix. action=speed: site, url, strategy mobile|"
        "desktop -> Core Web Vitals (PageSpeed Insights). action=performance: site, days -> Search Console clicks / impressions / "
        "CTR / position vs previous period, striking-distance + low-CTR opportunities, cannibalisation (needs her Search Console "
        "connected in the app). action=brief: keyword (new page plan). action=schema: kind local (LocalBusiness, default) | "
        "organization | website | breadcrumb | service | product | article, url (which page) -> JSON-LD draft. action=inspect: "
        "urls [her pages] -> Google's own index verdict per page (Search Console URL Inspection). action=crux -> 25 weeks of "
        "real-visitor speed (Chrome UX Report). action=gbp_post: "
        "topic, offer. action=review_reply: review, stars, reviewer. action=approve: draft_id, text (ONLY when she says it is "
        "final). action=task: task_id, status done|ignored|open. action=report (Excel). action=settings: weekday, morning_time. "
        "v0.317 HIRED SEO EMPLOYEE (only when she hired it in Employees): action=report_pdf (the monthly PDF report now), "
        "action=roadmap (rebuild the 90-day plan draft), action=plan_item: item_id, status planned|doing|waiting_her|done|skipped, "
        "action=indexnow (her IndexNow key file; once she puts it on the site, changed pages go to Bing / IndexNow weekly). "
        "v0.541 SEARCH INTEL: action=track: keywords [what people search] (remove=true to stop) -> followed daily from Search "
        "Console; action=rank_check: keywords (optional) -> exact Google position + top 3 via DataForSEO (her key, costs, runs in "
        "the background); action=keyword_ideas: keywords [seed words] -> monthly searches (Google Keyword Planner if her Google Ads "
        "is linked, else DataForSEO); action=ai_prompts: prompts [questions customers ask ChatGPT / Gemini] (add); action="
        "ai_suggest -> 10 such questions to offer her; action=ai_run -> ask ChatGPT / Gemini / Perplexity through their APIs: is "
        "she named, is her site cited, who is cited instead (priced per answer, her monthly ceiling, background); action=maps_grid: "
        "keyword, size 3|5|7 -> her Google Maps rank from a grid of points around her shop (her shop must be picked once in the "
        "app); action=competitors / backlinks / domain: domain (empty = hers) and action=gap: competitor (domain) -> DataForSEO "
        "data (her key; she joins DataForSEO only in the app, never a password in chat)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["site", "audit", "speed", "performance", "brief", "schema", "gbp_post", "review_reply",
                                               "approve", "task", "report", "settings", "report_pdf", "roadmap", "plan_item",
                                               "inspect", "crux", "indexnow", "track", "rank_check", "keyword_ideas",
                                               "ai_prompts", "ai_suggest", "ai_run", "maps_grid", "competitors", "backlinks",
                                               "gap", "domain"]},
         "keywords": {"type": "array", "items": {"type": "string"}}, "remove": {"type": "boolean"},
         "prompts": {"type": "array", "items": {"type": "string"}},
         "size": {"type": "integer"}, "domain": {"type": "string"}, "competitor": {"type": "string"},
         "kind": {"type": "string"}, "urls": {"type": "array", "items": {"type": "string"}},
         "item_id": {"type": "string"},
         "site": {"type": "string"}, "url": {"type": "string"}, "name": {"type": "string"}, "city": {"type": "string"},
         "state": {"type": "string"}, "street": {"type": "string"}, "pin": {"type": "string"}, "phone": {"type": "string"},
         "schema_type": {"type": "string"}, "hours": {"type": "string"}, "price_range": {"type": "string"},
         "services": {"type": "array", "items": {"type": "string"}}, "max_pages": {"type": "integer"}, "strategy": {"type": "string"},
         "days": {"type": "integer"}, "keyword": {"type": "string"}, "topic": {"type": "string"}, "offer": {"type": "string"},
         "review": {"type": "string"}, "stars": {"type": "integer"}, "reviewer": {"type": "string"}, "draft_id": {"type": "string"},
         "text": {"type": "string"}, "task_id": {"type": "string"}, "status": {"type": "string"}, "weekday": {"type": "integer"},
         "morning_time": {"type": "string"}},
         "required": ["action"]}},
    {"name": "seo_dekho", "description": (
        "Read SEO work (nothing changes). what=summary (score, open fixes, weekly numbers, Search Console link) | sites | tasks "
        "(status open|done|fixed|ignored) | pages | keywords (plan from her services + city, with Search Console positions) | "
        "drafts | gsc (connected? properties) | rules (Google spam policies she must not break + Business Profile checklist) | "
        "desk (v0.317 the hired SEO Employee: KPIs vs baseline, 90-day plan board, alerts, schedule; says if not hired) | "
        "health (v0.319 last audit: health score in 7 parts with critical/high/medium/low counts, E-E-A-T signals, local "
        "score, which AI search / training bots robots.txt lets in) | changes (what changed on her pages since the last audit) | "
        "updates (Google's confirmed core / spam updates, to explain a rise or drop) | ranks (v0.541 her tracked keywords: "
        "Search Console position + 7-day move + exact Google check) | ai (AI answers: % named / cited per engine, competitors "
        "named, sites cited instead, per question) | maps (her Maps grids: top-3 points, average rank, who leads) | intel "
        "(everything + this month's spend and DataForSEO status)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["summary", "sites", "tasks", "pages", "keywords", "drafts", "gsc", "rules", "desk",
                                             "health", "changes", "updates", "ranks", "ai", "maps", "intel"]},
         "site": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
SEO_LABELS = {"seo": "Doing the website's SEO", "seo_dekho": "Checking the SEO file"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..seo import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    site = _s(a.get("site"))
    try:
        if action == "site":
            biz = {k: a.get(k) for k in ("city", "state", "street", "pin", "phone", "schema_type", "hours", "price_range")}
            return S.save_site(t, _s(a.get("url")), _s(a.get("name")), site, a.get("services"), **biz)
        if action == "audit":
            return S.crawl(t, site, int(a.get("max_pages") or 25), conv)
        if action == "speed":
            return S.pagespeed(t, site, _s(a.get("url")), _s(a.get("strategy")) or "mobile")
        if action == "performance":
            return S.performance(t, site, int(a.get("days") or 28), conv)
        if action == "brief":
            return S.content_brief(t, _s(a.get("keyword")), site, conv)
        if action == "schema":
            return S.schema_draft(t, site, conv, _s(a.get("kind")), _s(a.get("url")))
        if action == "inspect":
            urls = [str(u) for u in (a.get("urls") or []) if str(u).strip()] or ([_s(a.get("url"))] if a.get("url") else None)
            rows = S.gsc_inspect(t, site, urls, limit=20)
            ok = [x for x in rows if not x.get("error")]
            return {"pages": rows, "say": f"According to Google, {sum(1 for x in ok if x['indexed'])} / {len(ok)} pages are indexed."}
        if action == "crux":
            return S.crux_history(t, site)
        if action == "gbp_post":
            return S.gbp_post(t, _s(a.get("topic")), _s(a.get("offer")), site, conv)
        if action == "review_reply":
            return S.review_reply(t, _s(a.get("review")), int(a.get("stars") or 0), _s(a.get("reviewer")), site, conv)
        if action == "approve":
            if not _owner(ctx):
                raise ToolError("Only the owner can say yes to finalising a draft.")
            return S.approve_draft(t, _s(a.get("draft_id")), _s(a.get("text")))
        if action == "task":
            return S.close_task(t, _s(a.get("task_id")), _s(a.get("status")) or "done")
        if action == "report":
            return S.report_file(t, site, conv)
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Owner only.")
            return S.save_settings(t, **{k: a[k] for k in ("weekday", "morning_time") if k in a})
        if action in INTEL_ACTIONS:
            return _intel_act(ctx, action, a)
        if action in ("report_pdf", "roadmap", "plan_item", "indexnow"):
            from ..employee import hire
            from ..seo import desk as D
            if not hire.is_hired(t, D.KEY):
                raise ToolError("SEO Specialist is not hired: this work happens after hiring one in Employees.")
            if action == "plan_item":
                return D.set_item(t, _s(a.get("item_id")), _s(a.get("status")))
            if action == "indexnow":
                return D.indexnow_key(t, site)
            sid = D.desk_view(t, site).get("site", {}).get("id")
            if not sid:
                raise ToolError("Onboarding first: add the website in Employees > SEO Specialist.")
            if action == "roadmap":
                return D.build_roadmap(t, sid)
            return D.monthly_report(t, sid, conv)
    except (S.SeoError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("invalid action")


INTEL_ACTIONS = ("track", "rank_check", "keyword_ideas", "ai_prompts", "ai_suggest", "ai_run", "maps_grid", "competitors",
                 "backlinks", "gap", "domain")


def _bg(fn, *args) -> dict[str, Any]:
    import threading

    def go():
        try:
            fn(*args)
        except Exception:   # noqa: BLE001 - the result / error is on the SEO desk view
            pass
    threading.Thread(target=go, daemon=True).start()
    return {"started": True, "say": "Work started - the result will arrive on the SEO desk (Search intel); check with seo_dekho shortly."}


def _intel_act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..seo import dfs
    from ..seo import intel as I
    t, site = ctx.tenant_id, _s(a.get("site"))
    kws = [str(x) for x in (a.get("keywords") or []) if str(x).strip()]
    try:
        if action == "track":
            return (I.untrack if a.get("remove") else I.track)(t, kws, site)
        if action == "rank_check":
            I._site(t, site)
            return _bg(I.check_serp, t, site, kws or None)
        if action == "keyword_ideas":
            r = I.keyword_research(t, kws, site)
            return {**r, "ideas": (r.get("ideas") or [])[:25]}
        if action == "ai_prompts":
            return I.add_prompts(t, [str(x) for x in (a.get("prompts") or [])], site)
        if action == "ai_suggest":
            return I.suggest_prompts(t, site)
        if action == "ai_run":
            I._site(t, site)
            return _bg(I.run_ai, t, site, None)
        if action == "maps_grid":
            I._site(t, site)
            return _bg(I.run_grid, t, _s(a.get("keyword")), site, a.get("size"), None)
        sv = I._site(t, site)
        dom = _s(a.get("domain")) or sv["domain"]
        if action == "competitors":
            return {"competitors": dfs.competitors(t, sv["id"], dom), "spend": dfs.status(t, sv["id"])}
        if action == "backlinks":
            return {**dfs.backlinks(t, sv["id"], dom), "spend": dfs.status(t, sv["id"])}
        if action == "domain":
            return {**dfs.domain_overview(t, sv["id"], dom), "spend": dfs.status(t, sv["id"])}
        if action == "gap":
            if not a.get("competitor"):
                raise ToolError("Which competitor to compare with? (domain)")
            return {**dfs.gap(t, sv["id"], sv["domain"], _s(a.get("competitor"))), "spend": dfs.status(t, sv["id"])}
    except (I.IntelError, dfs.DfsError) as ex:
        raise ToolError(str(ex))
    raise ToolError("invalid action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..seo import rules as R
    from ..seo import service as S
    t, site = ctx.tenant_id, _s(a.get("site"))
    try:
        if what == "summary":
            return S.summary(t, site)
        if what == "sites":
            return {"sites": S.sites(t)}
        if what == "tasks":
            return {"tasks": S.tasks(t, site, _s(a.get("status")) if a.get("status") is not None else "open")}
        if what == "pages":
            return {"pages": S.pages(t, site)}
        if what == "keywords":
            return S.keyword_plan(t, site)
        if what == "drafts":
            return {"drafts": S.drafts(t, site, _s(a.get("status")))}
        if what == "gsc":
            st = S.gsc_status(t)
            if st["connected"]:
                st["properties"] = S.gsc_properties(t)
            return st
        if what == "rules":
            return {"never": list(R.NEVER), "gbp_checklist": R.GBP_CHECKLIST, "cwv": R.CWV}
        if what == "desk":
            from ..seo import desk as D
            v = D.desk_view(t, site)
            if v.get("onboarded"):
                v.pop("sites", None)
                v.pop("shots", None)                  # pictures are for the screen, not the model
                v["open_tasks"] = v.get("open_tasks", [])[:10]
            return v
        if what == "health":
            pro = S.pro_view(t, site)
            return {k: pro.get(k) for k in ("at", "health", "eeat", "local", "ai_bots", "llms")}
        if what == "changes":
            pro = S.pro_view(t, site)
            return {"at": pro.get("at"), "changes": pro.get("drift") or [],
                    "say": f"{len(pro.get('drift') or [])} change(s) since the last check." if pro.get("drift") else "No change since the last check."}
        if what in ("ranks", "ai", "maps", "intel"):
            from ..seo import intel as I
            try:
                if what == "ranks":
                    v = I.ranks_view(t, site)
                    return {"keywords": [{k: x[k] for k in ("keyword", "position", "move_7d", "clicks_7d", "impressions_7d", "url", "exact")}
                                         for x in v["keywords"]], "note": v["note"]}
                if what == "ai":
                    v = I.ai_view(t, site)
                    v.pop("site", None)
                    for p in v["prompts"]:
                        for r in p["results"]:
                            r.pop("excerpt", None)
                    return v
                if what == "maps":
                    return I.grids_view(t, site)
                v = I.view(t, site)
                return {"settings": v["settings"], "spend": v["spend"], "dataforseo": v["dataforseo"],
                        "ranks": len(v["ranks"]["keywords"]), "ai": v["ai"]["summary"], "maps": len(v["maps"]["grids"])}
            except I.IntelError as ex:
                raise ToolError(str(ex))
        if what == "updates":
            from ..seo import pro as P
            return {"updates": [{"date": d, "name": n, "kind": k} for d, n, k in P.UPDATES[-12:]],
                    "source": "Google Search Status Dashboard / Search Central (confirmed updates only)"}
    except (S.SeoError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("invalid what")


async def seo(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def seo_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


SEO_HANDLERS = {"seo": seo, "seo_dekho": seo_dekho}
