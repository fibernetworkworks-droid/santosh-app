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
        "connected in the app). action=brief: keyword (new page plan). action=schema (LocalBusiness JSON-LD). action=gbp_post: "
        "topic, offer. action=review_reply: review, stars, reviewer. action=approve: draft_id, text (ONLY when she says it is "
        "final). action=task: task_id, status done|ignored|open. action=report (Excel). action=settings: weekday, morning_time. "
        "v0.317 HIRED SEO EMPLOYEE (only when she hired it in Employees): action=report_pdf (the monthly PDF report now), "
        "action=roadmap (rebuild the 90-day plan draft), action=plan_item: item_id, status planned|doing|waiting_her|done|skipped."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["site", "audit", "speed", "performance", "brief", "schema", "gbp_post", "review_reply",
                                               "approve", "task", "report", "settings", "report_pdf", "roadmap", "plan_item"]},
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
        "desk (v0.317 the hired SEO Employee: KPIs vs baseline, 90-day plan board, alerts, schedule; says if not hired)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["summary", "sites", "tasks", "pages", "keywords", "drafts", "gsc", "rules", "desk"]},
         "site": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
SEO_LABELS = {"seo": "Website ka SEO kar raha hoon", "seo_dekho": "SEO ki file dekh raha hoon"}


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
            return S.schema_draft(t, site, conv)
        if action == "gbp_post":
            return S.gbp_post(t, _s(a.get("topic")), _s(a.get("offer")), site, conv)
        if action == "review_reply":
            return S.review_reply(t, _s(a.get("review")), int(a.get("stars") or 0), _s(a.get("reviewer")), site, conv)
        if action == "approve":
            if not _owner(ctx):
                raise ToolError("Draft final karne ki haan sirf owner.")
            return S.approve_draft(t, _s(a.get("draft_id")), _s(a.get("text")))
        if action == "task":
            return S.close_task(t, _s(a.get("task_id")), _s(a.get("status")) or "done")
        if action == "report":
            return S.report_file(t, site, conv)
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            return S.save_settings(t, **{k: a[k] for k in ("weekday", "morning_time") if k in a})
        if action in ("report_pdf", "roadmap", "plan_item"):
            from ..employee import hire
            from ..seo import desk as D
            if not hire.is_hired(t, D.KEY):
                raise ToolError("SEO Specialist hired nahi hai: Employees mein hire karne ke baad yeh kaam hota hai.")
            if action == "plan_item":
                return D.set_item(t, _s(a.get("item_id")), _s(a.get("status")))
            sid = D.desk_view(t, site).get("site", {}).get("id")
            if not sid:
                raise ToolError("Pehle onboarding: Employees > SEO Specialist mein website jodiye.")
            if action == "roadmap":
                return D.build_roadmap(t, sid)
            return D.monthly_report(t, sid, conv)
    except (S.SeoError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


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
                v["open_tasks"] = v.get("open_tasks", [])[:10]
            return v
    except (S.SeoError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def seo(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def seo_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


SEO_HANDLERS = {"seo": seo, "seo_dekho": seo_dekho}
