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
        "checking a status, filling an online form. Describe the goal fully in one sentence with every detail the user "
        "gave (names, dates, numbers, city). It never logs in, never types passwords/OTPs/PINs/card/Aadhaar and never "
        "pays: it stops and shows the user an Open button for that step. Before anything that submits, sends, books "
        "or deletes, the user gets a confirm card. Slow (30 s to a few minutes); for long tasks it replies later in "
        "the chat by itself."),
     "input_schema": {"type": "object", "properties": {
         "task": {"type": "string", "description": "What to do and what to report back"},
         "start_url": {"type": "string", "description": "Optional official website to start on"}},
         "required": ["task"]}},
    {"name": "open_on_phone", "description": (
        "Open a website or link on the user's phone (in their browser or the matching app), when they want to see "
        "or use it themselves: 'IRCTC ki site khol do', 'YouTube pe yeh gaana kholo', a map link, a payment page."),
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "title": {"type": "string"}},
                      "required": ["url"]}},
]

WEB_LABELS = {"google_search": "Google par dhoondh raha hoon", "open_website": "Website padh raha hoon",
              "open_on_phone": "Phone par khol raha hoon", "browse_web": "Browser mein website par kaam kar raha hoon"}


async def google_search(ctx: Ctx, query, **_):
    try:
        return await web.google_search(str(query)[:400])
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
    try:
        res = await asyncio.to_thread(browser.start, ctx.tenant_id, task[:4000], url[:2000], _wait)
    except browser.BrowserError as e:
        raise ToolError(str(e))
    return await asyncio.to_thread(browser.deliver, ctx.tenant_id, ctx.conversation_id, res, False)


WEB_HANDLERS = {"browse_web": browse_web, "google_search": google_search, "open_website": open_website, "open_on_phone": open_on_phone}
