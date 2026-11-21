"""v0.999.82 D8 wave 5: a website written in React, LIVE on its own address (owner's choice: "Own address per site").

Under Hoola's own address a React website is sealed (CSP sandbox: a blank origin, so no site can ever read another's
data - and so it keeps nothing: no cart after a reload, no saved progress). On ITS OWN address (her domain, or its free
<name>.<SITES_BASE_DOMAIN> address - each its own origin) there is nothing to seal it from, so it goes out unsealed:

  publish()   her tap "Go live" puts the React app's built version on her address: the pre-rendered pages with every
              placeholder filled for that address (links, canonical, sitemap, robots), its files as they are, nothing of
              the build's own (__pages.json, __spa.html). Swapped in whole, like her HTML website.
  blockers()  what stops it going live: not built, a build that failed, blanks still marked "(add yours)", a draft.
  headers()   the React page's own security policy WITHOUT the sandbox (scripts only from itself, forms / shop / booking
              only to itself), HSTS, no sniffing; the visitor's browser may keep the cart and her ticks there.
  allowed()   on her address only THIS site's own visitor addresses reach Hoola (its forms, booking, shop) - nothing else
              of Hoola's API (as before for her HTML website).

The sealed preview under Hoola's address stays as it was (drafts, the Studio)."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.site")
MARK = "_hoola_react"                                # in the published folder: this address serves a React website
INTERNAL = ("__pages.json", "__spa.html")


def app_of(r) -> Any | None:
    """The App Engine app this website is written into, when it has a built version."""
    from ..appengine import service as AE
    from . import prototype as PT
    ref = PT.react_link(r).get("id")
    if not ref:
        return None
    try:
        app = AE._load(r.tenant_id, ref)
    except Exception:                                # noqa: BLE001 - the app was removed
        return None
    return app


def is_react(r) -> bool:
    return app_of(r) is not None


def version(r) -> int:
    app = app_of(r)
    return int(app.version or 0) if app else 0


def dist(r) -> Path | None:
    from ..appengine import service as AE
    app = app_of(r)
    if not app or not app.version:
        return None
    d = AE.ver_dir(app, int(app.version)) / "dist"
    return d if (d / "index.html").is_file() else None


def blockers(r) -> list[str]:
    from ..appengine import service as AE
    out: list[str] = []
    app = app_of(r)
    if getattr(r, "draft_of", ""):
        out.append("this is a draft; accept it into the website (Drafts tab), then put the website live")
    if not app or not app.version or dist(r) is None:
        out.append("the React website has no built version yet")
        return out
    if getattr(app, "dirty", False):
        out.append("the React website is being built again right now - go live when it is ready")
    try:
        bl = json.loads((AE.src_dir(app) / ".hoola" / "blanks.json").read_text("utf-8")).get("blanks") or []
    except (OSError, ValueError):
        bl = []
    if bl:
        out.append("fill in before going live: " + ", ".join(map(str, bl[:6])))
    pages = AE.pages_of(dist(r))
    if not pages.get("ok"):
        out.append("its pages were not pre-rendered (" + str(pages.get("why") or "the last build") + ")")
    return out


def fingerprint(r) -> str:
    d = dist(r)
    if d is None:
        return ""
    st = (d / "index.html").stat()
    return f"{version(r)}:{st.st_mtime_ns:x}"


def _fill(txt: str, origin: str) -> str:
    txt = txt.replace("__hoola_origin__/__hoola_base__", origin)
    return txt.replace("__hoola_origin__", origin).replace("/__hoola_base__", "")


def publish(r, host: str, out: Path) -> int:
    """Write the React website's built version into `out` for https://<host>/. Returns the version published."""
    src = dist(r)
    if src is None:
        raise ValueError("the React website has no built version yet")
    if out.exists():
        shutil.rmtree(out)
    origin = f"https://{host}"
    for f in src.rglob("*"):
        rel = f.relative_to(src)
        if f.is_symlink() or rel.parts[0] in INTERNAL or any(p.startswith(".") for p in rel.parts):
            continue
        dst = out / rel
        if f.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        ext = f.suffix.lower()
        if ext == ".html":
            txt = _fill(f.read_text("utf-8", "replace"), origin)
            txt = re.sub(r"<head>", '<head>\n    <base href="/">', txt, count=1)
            dst.write_text(txt, "utf-8")
        elif ext in (".xml", ".txt"):
            dst.write_text(_fill(f.read_text("utf-8", "replace"), origin), "utf-8")
        else:
            try:
                os.link(f, dst)
            except OSError:
                shutil.copy2(f, dst)
    (out / MARK).write_text(json.dumps({"site": r.id, "version": version(r)}), "utf-8")
    return version(r)


def headers() -> dict[str, str]:
    from ..appengine import service as AE
    return {"Content-Security-Policy": AE.CSP, "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin", "Strict-Transport-Security": "max-age=31536000",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()"}


def allowed(site_id: str, path: str) -> bool:
    """The visitor addresses of THIS site that its React pages call on her address (same origin): its forms, booking
    and shop, and (v0.999.82 wave 7) its member app - sign-in, her lists, the visitor's own account. Every rule is
    checked by the member app itself; the preview's own data (<site>~p) never answers on her address."""
    sid = re.escape(site_id or "")
    return bool(sid) and bool(re.match(rf"^/api/(site-forms|site-shop|site-app)/{sid}(/|$)", path or ""))
