"""Internet tools: Google Search, reading websites, opening a site on the phone."""
from __future__ import annotations

from .. import web
from .life_tools import _device_action
from .tools import Ctx, ToolError

WEB_TOOLS = [
    {"name": "google_search", "description": (
        "Search Google for anything current or factual: news, prices, cricket scores, train/flight timings, shop "
        "hours and phone numbers, government rules, product specs, exchange rates, holidays, people and companies. "
        "Returns a short answer plus source pages. Use it whenever the answer could have changed since your training "
        "or you are not sure. Write the query the way a person types into Google."),
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "web_sources", "description": (
        "Read what the web actually says: searches and returns short QUOTED excerpts from the best pages with their "
        "links (Parallel). Use it when the answer must stand on the sources' own words (checking a claim, comparing "
        "what sites say, a rule or price you will quote) or when google_search is not answering. Give urls to read "
        "specific pages instead of searching. Only the question / links are sent. Quote and cite the links you use."),
     "input_schema": {"type": "object", "properties": {
         "question": {"type": "string", "description": "What to find out, in one clear sentence"},
         "search_queries": {"type": "array", "items": {"type": "string"}, "description": "1-3 short keyword searches"},
         "urls": {"type": "array", "items": {"type": "string"}, "description": "Read these pages instead of searching"}},
         "required": ["question"]}},
    {"name": "open_website", "description": (
        "Open a web page and read its text, like a person reading the site: a link the user gives you, an official "
        "page from google_search sources, a price or timing on a specific site. Returns the page title, text and links "
        "(follow a link by calling this again). Pages that need login or are built only with JavaScript may come back "
        "nearly empty; then use google_search instead."),
     "input_schema": {"type": "object", "properties": {"url": {"type": "string", "description": "Full link or a domain like irctc.co.in"}},
                      "required": ["url"]}},
    {"name": "browse_web", "description": (
        "Santosh's own web browser (a real Chrome on the server, browser-use): do a task on a website step by step "
        "when google_search/open_website aren't enough: JavaScript sites, clicking through menus, comparing on a site, "
        "checking a status. Forms / applications / anything with login, Aadhaar, PAN, OTP: use computer_operator "
        "instead (it fills them). Describe the goal fully in one sentence with every detail the user "
        "gave (names, dates, numbers, city; ID numbers as their {id:...} reference - it types Aadhaar / PAN / any number). "
        "It never logs in, never types passwords/OTPs/PINs/card numbers and never "
        "pays: it stops and shows the user an Open button for that step. Before anything that submits, sends, books "
        "or deletes, the user gets a confirm card. Slow (30 s to a few minutes); for long tasks it replies later in "
        "the chat by itself."),
     "input_schema": {"type": "object", "properties": {
         "task": {"type": "string", "description": "What to do and what to report back"},
         "start_url": {"type": "string", "description": "Optional official website to start on"}},
         "required": ["task"]}},
    {"name": "browse_result", "description": (
        "Status or final answer of a Santosh Browser task (session_id from browse_web). Use when the user asks what "
        "happened with a website task, or to get the result of one that was still running."),
     "input_schema": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}},
    {"name": "open_on_phone", "description": (
        "Open a website or link on the user's phone (in their browser or the matching app), when they want to see "
        "or use it themselves: 'IRCTC ki site khol do', 'YouTube pe yeh gaana kholo', a map link, a payment page."),
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "title": {"type": "string"}},
                      "required": ["url"]}},
]

WEB_LABELS = {"google_search": "Google par dhoondh raha hoon", "web_sources": "Web ke pages padh raha hoon", "open_website": "Website padh raha hoon",
              "open_on_phone": "Phone par khol raha hoon", "browse_web": "Browser mein website par kaam kar raha hoon",
              "browse_result": "Browser ka nateeja dekh raha hoon"}


async def google_search(ctx: Ctx, query, **_):
    try:   # v0.91 when Google Search is unreachable, Parallel answers with quotes from real pages instead
        return await web.search_any(str(query)[:400])
    except web.WebError as e:
        raise ToolError(str(e))


async def web_sources(ctx: Ctx, question, search_queries=None, urls=None, **_):
    qs = [str(q) for q in (search_queries or []) if str(q).strip()] if isinstance(search_queries, list) else None
    us = [str(u) for u in (urls or []) if str(u).strip()] if isinstance(urls, list) else None
    try:
        return await web.parallel_search(str(question)[:2000], qs, us)
    except web.WebError as e:
        raise ToolError(str(e))


async def open_website(ctx: Ctx, url, **_):
    try:
        return await web.open_website(str(url))
    except web.WebError as e:
        raise ToolError(str(e))


async def open_on_phone(ctx: Ctx, url, title=None, **_):
    url = str(url).strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    return _device_action(ctx, "open_url", {"url": url[:2000], "title": (title or "")[:120]},
                          "The phone opens it in the browser; tell the user it is opening.")


async def browse_web(ctx: Ctx, task, start_url=None, _wait=None, **_):
    import asyncio

    from .. import browser
    task = str(task or "").strip()
    if len(task) < 3:
        raise ToolError("Say what to do on the website")
    url = str(start_url or "").strip()
    if url and not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    from .. import idvault
    try:   # v0.81 {id:...} references become the real number for the browser (it types Aadhaar / PAN / any number)
        task, _kinds = idvault.fill_value(task, ctx.tenant_id)
    except idvault.VaultError as e:
        raise ToolError(str(e))
    try:
        res = await asyncio.to_thread(browser.start, ctx.tenant_id, task[:4000], url[:2000], _wait, ctx.conversation_id)
    except browser.BrowserError as e:
        raise ToolError(str(e))
    out = await asyncio.to_thread(browser.deliver, ctx.tenant_id, ctx.conversation_id, res, False)
    return _masked(out)


def _masked(v):
    """Full ID numbers in what comes back are masked before the chat model reads it."""
    from ..operator.browser import mask_ids
    if isinstance(v, str):
        return mask_ids(v)
    if isinstance(v, dict):
        return {k: _masked(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_masked(x) for x in v]
    return v


async def browse_result(ctx: Ctx, session_id, **_):
    import asyncio

    from .. import browser
    try:
        res = await asyncio.to_thread(browser.get, ctx.tenant_id, str(session_id), 4)
    except browser.BrowserError as e:
        raise ToolError(f"That browser task isn't available any more ({e}). Run browse_web again if needed.")
    res.pop("screenshot_jpeg_b64", None)
    if res.get("status") in ("running", "starting"):
        return {"status": "running", "steps_so_far": res.get("steps", 0), "url": res.get("url", ""),
                "say": "Still working; tell the user it's on it (live card in chat)."}
    return {"status": res.get("status"), "answer": res.get("summary", ""), "url": res.get("url", ""),
            "reason": res.get("reason", "")}


WEB_HANDLERS = {"browse_result": browse_result, "browse_web": browse_web, "google_search": google_search, "web_sources": web_sources, "open_website": open_website, "open_on_phone": open_on_phone}
