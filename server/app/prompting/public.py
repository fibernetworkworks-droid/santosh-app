"""P11 public recipe pages (docs/HOOLA_PROMPTING_PLAN.md part 11 row P11): /prompts and /prompts/<recipe> on the Hoola
website, so a person searching "diwali poster prompt" finds a Hoola recipe and can open it in Hoola Prompting.

Each page is drawn from the recipe table and the engine dialect at request time - the example prompt is the recipe
filled with its own example blanks, exactly what the workbench would make. Hoola's starters always; approved community
recipes only while the community switch is on, under the name their writer chose. Nothing a user typed into her own
workbench ever reaches these pages. Same shell, styles and headers as the rest of the website (static/site)."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from . import anatomy as A

SITE = Path(__file__).resolve().parents[1] / "static" / "site"
BASE = "https://hoola.ainewtika.com"


def _shell() -> tuple[str, str]:
    page = (SITE / "pricing.html").read_text(encoding="utf-8")
    head, rest = page.split('<main id="main">', 1)
    tail = rest.split("</main>", 1)[1]
    head = head.replace(' aria-current="page"', "")
    return head, tail


def _page(title: str, desc: str, body: str, canonical: str, ld: dict[str, Any] | None = None) -> str:
    head, tail = _shell()
    t, d = html.escape(title), html.escape(desc)
    head = re.sub(r"<title>.*?</title>", f"<title>{t}</title>", head, count=1, flags=re.S)
    head = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{d}">', head, count=1)
    head = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{t}">', head, count=1)
    head = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{d}">',
                  head, count=1)
    extra = f'<link rel="canonical" href="{BASE}{html.escape(canonical)}">\n'
    if ld:
        extra += '<script type="application/ld+json">' + json.dumps(ld).replace("</", "<\\/") + "</script>\n"
    head = head.replace("</head>", extra + "</head>", 1)
    return head + '<main id="main">' + body + "</main>" + tail


def _all(section: str = "") -> list[dict[str, Any]]:
    from . import recipes as R
    from . import samudaay as SM
    out = [r for r in R.RECIPES if not section or r["section"] == section]
    try:
        out += [{**c, "community": True} for c in SM.listing(section)]
    except Exception:       # noqa: BLE001
        pass
    return out


def _example(rid: str) -> dict[str, Any] | None:
    from . import dialect as D
    from . import recipes as R
    try:
        if rid.startswith("com:"):
            b = R.use(rid)["brief"]
        else:
            r = next(x for x in R.RECIPES if x["id"] == rid)
            b = R.use(rid, {x["key"]: x["eg"] for x in r["blanks"]})["brief"]
        return D.render(b)
    except Exception:       # noqa: BLE001
        return None


def _e(s: Any) -> str:
    return html.escape(str(s or ""))


def index() -> str:
    groups = []
    for sec in A.ORDER:
        rows = _all(sec)
        if not rows:
            continue
        cards = "".join(
            f'<a class="plan2" href="/prompts/{_e(r["id"])}" style="text-decoration:none"><h3 class="h3">{_e(r["title"])}</h3>'
            f'<p class="small muted">{_e(r.get("makes"))}</p>'
            + (f'<p class="small muted">By {_e(r.get("by"))}</p>' if r.get("community") else "") + "</a>"
            for r in rows)
        groups.append(f'<section class="band" id="{_e(sec)}"><div class="wrap"><div class="sec-head"><h2 class="h2">'
                      f'{_e(A.SECTIONS[sec]["label"])}</h2><p class="sub">Prompts for {_e(A.SECTIONS[sec]["makes"])}.</p></div>'
                      f'<div class="plans">{cards}</div></div></section>')
    n = sum(len(_all(s)) for s in A.ORDER)
    body = ('<div class="wrap"><div class="phead"><span class="crumb">Prompt recipes</span>'
            '<h1 class="h1">Prompts that say everything the AI needs.</h1>'
            f'<p class="lead">{n} ready recipes for posters, reels, websites, apps, messages, documents and more. Fill a few '
            'blanks in Hoola Prompting; anything you leave empty becomes a question, never a made-up value.</p>'
            '<div class="ctas"><a class="btn pri" href="/console/prompting">Open Hoola Prompting</a></div></div></div>'
            + "".join(groups))
    return _page("Prompt recipes · Hoola", "Ready prompt recipes for posters, reels, websites, apps and business messages, "
                 "with the parts a good prompt needs.", body, "/prompts")


def recipe(rid: str) -> str | None:
    rows = {r["id"]: r for r in _all()}
    r = rows.get(rid)
    if r is None:
        return None
    sec = A.SECTIONS[r["section"]]
    out = _example(rid)
    blanks = r.get("blanks") or []
    parts = [sl for sl in A.slots(r["section"]) if sl.get("required")]
    body = (f'<div class="wrap"><div class="phead"><a class="crumb" href="/prompts#{_e(r["section"])}">'
            f'{_e(sec["label"])} prompts</a><h1 class="h1">{_e(r["title"])}</h1><p class="lead">{_e(r.get("makes"))}.</p>'
            + (f'<p class="small muted">A community recipe by {_e(r.get("by"))}.</p>' if r.get("community") else "")
            + f'<div class="ctas"><a class="btn pri" href="/console/prompting#/r/{_e(rid)}">Use this recipe in Hoola</a>'
            '<a class="btn ghost" href="/prompts">All recipes</a></div></div></div>')
    if blanks:
        body += ('<section class="band alt"><div class="wrap"><div class="sec-head"><h2 class="h2">You fill in</h2></div><ul>'
                 + "".join(f'<li><b>{_e(b["label"])}</b> <span class="muted">for example: {_e(b.get("eg"))}</span></li>'
                           for b in blanks) + "</ul></div></section>")
    if out:
        body += ('<section class="band"><div class="wrap"><div class="sec-head"><h2 class="h2">The prompt it makes</h2>'
                 '<p class="sub">Filled with the example blanks above, in the words Hoola sends to the '
                 f'{_e(sec["engine"])}.</p></div><pre class="tbl" style="white-space:pre-wrap;padding:18px;overflow:auto">'
                 f'{_e(out["prompt"])}</pre></div></section>')
    body += ('<section class="band alt"><div class="wrap"><div class="sec-head"><h2 class="h2">What a complete '
             f'{_e(sec["label"].lower())} prompt has</h2></div><ul>'
             + "".join(f'<li><b>{_e(sl["label"])}</b> <span class="muted">{_e(sl["q"])}</span></li>' for sl in parts)
             + "</ul></div></section>")
    ld = {"@context": "https://schema.org", "@type": "HowTo", "name": r["title"], "description": r.get("makes") or "",
          "step": [{"@type": "HowToStep", "text": f"Fill in: {b['label']}"} for b in blanks]
          + [{"@type": "HowToStep", "text": "Open the recipe in Hoola Prompting and run it."}]}
    return _page(f"{r['title']} prompt · Hoola", f"{r.get('makes') or r['title']}: a ready prompt recipe with the parts a "
                 "good prompt needs.", body, f"/prompts/{rid}", ld)


def sitemap() -> str:
    urls = ["/prompts"] + [f"/prompts/{r['id']}" for r in _all()]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"<url><loc>{BASE}{html.escape(u)}</loc></url>\n" for u in urls) + "</urlset>\n")
