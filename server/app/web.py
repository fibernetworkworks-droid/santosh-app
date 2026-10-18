"""Internet access for Santosh: real Google Search (via the Gemini API's Google Search grounding)
and reading any public web page.

Safety: pages are fetched only from the public internet. Private, loopback and link-local addresses
are refused (and re-checked on every redirect), so nobody can use Santosh to reach services that run
on the server itself or on the local network.
"""
from __future__ import annotations

import asyncio
import html
import ipaddress
import logging
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from .config import get_settings

log = logging.getLogger("santosh.web")

SEARCH_MODELS = ("gemini-flash-latest", "gemini-3.5-flash", "gemini-2.5-flash")
MAX_PAGE_BYTES = 3_000_000
MAX_TEXT = 14_000
UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0 Mobile Safari/537.36 Santosh/0.5")


_transport = None   # tests plug in httpx.MockTransport


class WebError(Exception):
    pass


# ---------------- Google Search ----------------
async def google_search(query: str) -> dict:
    """Ask Gemini with Google Search grounding: a short factual answer plus the pages it came from."""
    st = get_settings()
    if not st.gemini_api_key:
        raise WebError("Google Search needs GEMINI_API_KEY on the server.")
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=st.gemini_api_key)
    models = [st.gemini_search_model] if st.gemini_search_model else []
    models += [m for m in SEARCH_MODELS if m not in models]
    prompt = (f"Search Google and answer for a user in India: {query}\n"
              "Give the facts that answer it (numbers, dates, names, prices, timings) in a few short lines. "
              "Say plainly if results disagree or are unclear.")
    last = None
    for model in models:
        try:
            r = await asyncio.wait_for(client.aio.models.generate_content(
                model=model, contents=prompt,
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])), timeout=40)
        except Exception as e:   # unknown model name, quota, timeout: try the next one
            last = e
            log.warning("google search with %s failed: %s", model, e)
            continue
        sources, seen = [], set()
        for cand in r.candidates or []:
            gm = cand.grounding_metadata
            for ch in (gm.grounding_chunks if gm and gm.grounding_chunks else []):
                w = ch.web
                if w and w.uri and w.uri not in seen:
                    seen.add(w.uri)
                    sources.append({"title": w.title or w.domain or "", "url": w.uri})
        searched = []
        for cand in r.candidates or []:
            gm = cand.grounding_metadata
            if gm and gm.web_search_queries:
                searched += gm.web_search_queries
        return {"query": query, "answer": (r.text or "").strip(), "sources": sources[:8], "searched_for": searched[:4]}
    raise WebError(f"Google Search is not reachable right now: {last}")


# ---------------- reading web pages ----------------
def _public_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise WebError(f"Website '{host}' not found.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise WebError("That address is not on the public internet, so Santosh won't open it.")


def _check_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise WebError("Only normal http(s) website links can be opened.")
    if p.port not in (None, 80, 443):
        raise WebError("Only standard website ports (80/443) are allowed.")
    _public_host(p.hostname)
    return url


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "iframe", "head"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table", "ul", "ol", "header", "footer"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self._skip = 0
        self._in_title = False
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in self.SKIP and tag != "head":
            self._skip += 1
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._link_text = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self.SKIP and tag != "head" and self._skip:
            self._skip -= 1
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag == "a" and self._href:
            t = " ".join("".join(self._link_text).split())
            if t and len(self.links) < 40:
                self.links.append((t[:80], self._href))
            self._href = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if self._skip:
            return
        self.parts.append(data)
        if self._href is not None:
            self._link_text.append(data)


def html_to_text(raw: str, base_url: str) -> dict:
    p = _Text()
    try:
        p.feed(raw)
    except Exception:
        pass
    text = "".join(p.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    links = []
    for t, href in p.links:
        full = urljoin(base_url, href)
        if full.startswith("http"):
            links.append({"text": t, "url": full})
    return {"title": html.unescape(p.title.strip())[:200], "text": text, "links": links[:25]}


async def open_website(url: str) -> dict:
    """Fetch a public page and return its readable text (what a person would read on it)."""
    url = _check_url(url)
    async with httpx.AsyncClient(timeout=20, follow_redirects=False, transport=_transport, headers={"User-Agent": UA, "Accept-Language": "en-IN,hi;q=0.8"}) as c:
        for _ in range(6):
            try:
                async with c.stream("GET", url) as r:
                    if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                        url = _check_url(urljoin(url, r.headers["location"]))   # re-check every hop
                        continue
                    if r.status_code >= 400:
                        raise WebError(f"The website answered with error {r.status_code}.")
                    ctype = r.headers.get("content-type", "")
                    body = b""
                    async for chunk in r.aiter_bytes():
                        body += chunk
                        if len(body) > MAX_PAGE_BYTES:
                            break
                    final = str(r.url)
                    break
            except httpx.HTTPError as e:
                raise WebError(f"Could not open the website: {e}")
        else:
            raise WebError("The website redirected too many times.")
    raw = body.decode(r.encoding or "utf-8", errors="replace")
    if "html" in ctype or raw.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
        page = html_to_text(raw, final)
    elif ctype.startswith("text/") or "json" in ctype or "xml" in ctype:
        page = {"title": "", "text": raw, "links": []}
    else:
        raise WebError(f"This link is a file ({ctype or 'unknown type'}), not a web page Santosh can read.")
    text = page["text"]
    note = None
    if len(text) < 200:
        note = ("The page has almost no readable text; it probably builds itself with JavaScript or needs a login. "
                "Try google_search for the same information instead.")
    return {"url": final, "title": page["title"], "text": text[:MAX_TEXT], "truncated": len(text) > MAX_TEXT,
            "links": page["links"], **({"note": note} if note else {})}
