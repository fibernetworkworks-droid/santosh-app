"""The web_clone tool: the avatar clones a website the owner points her at.

Modes: learn (rebuild + document, the default), migrate (rebuild the owner's OWN site so it can
move), archive (a static keepsake). The pipeline never re-publishes: the project lands in the
owner's workspace, nothing is deployed anywhere. The brand law: cloning to LEARN from a
third-party site is fine; re-publishing someone else's live brand as one's own is refused -
_looks_like_own_or_reference guards the famous-brand names, and the description tells the model
the same. Honest line in the output: not pixel-perfect on JS-heavy sites; static / semi-static
pages are.
"""
from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from typing import Any

from .tools import Ctx, ToolError
from ..webclone import assemble, capture, endpoints_adapter

# Famous live brands: cloning one to LEARN is fine, re-publishing it as the owner's is not.
# Own-domain escapes are checked first (the owner's own site is always theirs to migrate).
_FAMOUS = re.compile(
    r"(^|\.)(google|youtube|facebook|instagram|whatsapp|amazon|flipkart|netflix|linkedin|twitter|x|"
    r"apple|microsoft|openai|anthropic|zomato|swiggy|paytm|phonepe|irctc|sbi|hdfcbank|icicibank|"
    r"airtel|jio|tata|infosys|wipro|tcs|github|gitlab|dropbox|spotify|uber|ola|makemytrip|"
    r"booking\.com|airbnb|ebay|paypal|stripe|shopify|wordpress|wix|squarespace)\.(com|co|io|in|net|org|dev|ai)$",
    re.I)

_MAX_DOM_CHARS = 3_000_000


def _looks_like_own_or_reference(url: str, own_domains: tuple[str, ...] = ()) -> tuple[bool, str]:
    """(is_famous_brand, why). The owner's own domains (and localhost-style hosts) are never famous."""
    host = (re.sub(r"^[a-z]+://", "", (url or "").strip(), flags=re.I).split("/")[0] or "").lower()
    if not host:
        return False, ""
    for dom in own_domains:
        if host == dom.lower() or host.endswith("." + dom.lower()):
            return False, ""
    if host.startswith(("localhost", "127.", "0.0.0.0", "192.168.", "10.")):
        return False, ""
    m = _FAMOUS.search(host)
    if m:
        return True, f"{host} is a live third-party brand"
    return False, ""


def _own_domains(ctx: Ctx) -> tuple[str, ...]:
    getter = getattr(ctx, "setting", None)
    raw = ""
    if callable(getter):
        try:
            raw = getter("webclone_own_domains") or ""
        except Exception:
            raw = ""
    return tuple(d.strip().lower() for d in raw.split(",") if d.strip())


def _project_root(ctx: Ctx, slug: str) -> Path:
    """Per-tenant workspace dir, same pattern as the REA cache (settings-driven, hash-suffixed)."""
    from ..settings import get_settings

    import hashlib
    s = get_settings()
    base = Path(getattr(s, "webclone_home", "") or (Path(getattr(s, "pc_files_dir", "/tmp/hoola")).parent / "webclone_home"))
    h = hashlib.sha1((ctx.tenant_id or "anon").encode("utf-8")).hexdigest()[:16]
    d = base / f"{h}" / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


async def web_clone(ctx: Ctx, url: str = "", mode: str = "learn", name: str = "", **_) -> dict[str, Any]:
    if not (url or "").strip():
        raise ToolError("Which website? Give the link (url).")
    mode = (mode or "learn").lower()
    if mode not in ("learn", "migrate", "archive"):
        raise ToolError("Give mode as learn / migrate / archive.")
    own = _own_domains(ctx)
    famous, why = _looks_like_own_or_reference(url, own)
    if famous:
        raise ToolError(
            f"{why}. Cloning someone else's live brand site and passing it off as your own is not allowed - that is brand theft. "
            "The owner can LEARN from its design and build her own site (web studio), or a similar layout without the brand "
            "- but this tool will not work on that link.")

    slug = re.sub(r"[^a-z0-9-]+", "-", (name or url).lower()).strip("-")[:40] or "site"
    work = _project_root(ctx, f"{slug}-{int(time.time())}")

    # ---- stage 1: capture (sync playwright inside a worker thread)
    try:
        manifest = await asyncio.to_thread(capture.capture, url, work, ctx.tenant_id or "")
    except capture.CaptureError as e:
        raise ToolError(str(e))

    # ---- stage 2: endpoints map (static scanner over the bundle)
    ep = await asyncio.to_thread(endpoints_adapter.scan, work, slug)

    # ---- stage 3: assemble the Next.js project
    summary = await asyncio.to_thread(assemble.assemble_project, work, work / "project",
                                      endpoints_md=_endpoints_md(ep))

    return {
        "url": manifest["url"], "title": manifest.get("title", ""), "mode": mode,
        "bundle": str(work), "project": summary["project"],
        "captured": {"css": manifest["counts"]["css"], "assets": manifest["counts"]["assets"],
                     "js_kept_for_rea": manifest["counts"]["js"],
                     "skipped": manifest["counts"]["skipped"], "dom_chars": manifest.get("dom_chars", 0)},
        "rebuild": summary,
        "endpoints": {"counts": ep["counts"], "top_hosts": ep["top_hosts"],
                      "api_paths": ep["api_paths"], "urls": ep["urls"][:12], "ips": ep["ips"][:5]},
        "notes": manifest.get("notes", []) + ep.get("limits", [])[:3] + [
            "Honest line: not pixel-perfect on JS-heavy sites; static / semi-static pages are. "
            "Original JS behaviour is static (kept in the bundle for REA); single page; nothing was published."],
    }


def _endpoints_md(ep: dict[str, Any]) -> str:
    lines = ["# Endpoints found in the capture", "",
             "Static scan of the bundle (the appcheck scanner - it reads bytes, never runs them). "
             "Use it to wire the rebuild's own fetches against what the original talked to.", ""]
    lines.append(f"- urls: {ep['counts'].get('url', 0)}, api paths: {ep['counts'].get('api_path', 0)}, "
                 f"hosts: {ep['counts'].get('host', 0)}, ips: {ep['counts'].get('ip', 0)}")
    if ep.get("top_hosts"):
        lines.append("")
        lines.append("## Top hosts")
        lines += [f"- {h}" for h in ep["top_hosts"][:15]]
    if ep.get("api_paths"):
        lines.append("")
        lines.append("## API paths")
        lines += [f"- `{p}`" for p in ep["api_paths"][:20]]
    lines.append("")
    return "\n".join(lines)


WEBCLONE_TOOLS = [
    {"name": "web_clone", "description": (
        "Clone a website the owner points her at: a clean Next.js (app-router) rebuild of the page plus a "
        "documented map of the endpoints / hosts / API paths the original talks to. Modes: learn (rebuild and "
        "document, the default), migrate (the owner's OWN site so it can move), archive (a static keepsake). "
        "Use it on 'is site ko clone kar do', 'is website ka rebuild banao', 'site ko archive kar do'. The page "
        "is captured with a headless browser AFTER its JS ran, CSS / images / fonts come local, two screenshots "
        "are kept, and the project lands in the owner's workspace - NOTHING is ever published or deployed. "
        "Honest limits, said to the user every time: the original site's JavaScript behaviour is static (forms, "
        "menus and fetches stay as captured; the JS bundles are kept for REA instead), it is a single page, and "
        "the rebuild is not pixel-perfect on JS-heavy sites - static / semi-static pages are. REFUSES to clone a "
        "third-party live brand (google, amazon, zomato, bank sites...) - that is brand theft; learning from its "
        "design and building the owner's own site in the web studio is the right answer. For git repositories "
        "the user wants cloned, that is git clone - not this tool; for building a NEW website from words, that "
        "is the website builder - not this tool."),
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string", "description": "the website link to clone"},
         "mode": {"type": "string", "enum": ["learn", "migrate", "archive"],
                  "description": "learn = rebuild + document (default), migrate = owner's own site moving, "
                                 "archive = static keepsake"},
         "name": {"type": "string", "description": "optional project / folder name"},
     }, "required": ["url"]}},
]
WEBCLONE_LABELS = {"web_clone": "Cloning the website: capture, endpoints, Next.js rebuild"}
WEBCLONE_HANDLERS = {"web_clone": web_clone}
