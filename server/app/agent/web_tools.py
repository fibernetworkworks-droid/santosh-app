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
    {"name": "open_on_phone", "description": (
        "Open a website or link on the user's phone (in their browser or the matching app), when they want to see "
        "or use it themselves: 'IRCTC ki site khol do', 'YouTube pe yeh gaana kholo', a map link, a payment page."),
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "title": {"type": "string"}},
                      "required": ["url"]}},
]

WEB_LABELS = {"google_search": "Google par dhoondh raha hoon", "open_website": "Website padh raha hoon",
              "open_on_phone": "Phone par khol raha hoon"}


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


WEB_HANDLERS = {"google_search": google_search, "open_website": open_website, "open_on_phone": open_on_phone}
