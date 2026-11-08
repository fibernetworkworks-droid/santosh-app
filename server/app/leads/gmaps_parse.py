"""v0.543.0 P3 THE SCRAPE LANE - the Google Maps PUBLIC LISTING parser (docs/LEADS_PLAN.md section 5.1).

THE PORT LAW, said out loud: nothing from gosom/google-maps-scraper or botasaurus is vendored (the crawl4ai
port is the precedent, the html2text GPL episode the cautionary tale). Their PUBLISHED IDEAS are re-implemented
here with our own hands and our own tests:

- ONE request shape: a /maps/search GET carrying the query, the cell's @lat,lng,zoom viewport, and the pb
  page-size parameter (`!7i20!8iNN` = 20 listings a page; the ~120-listing ceiling is walked PAGE BY PAGE,
  PAGES_PER_CELL_MAX pages a cell). The exact live pb shape is one of the plan's three named unknowns - her
  first live run confirms or corrects it; the builder is ONE function so a correction is one line.
- THE PARSER: Google embeds the listing data as positional JSON arrays under `window.APP_INITIALIZATION_STATE`
  (gosom's ParseSearchResults / EntryFromJSON idea). Every field's position is a NAMED CONSTANT below with the
  sample that proves it; the reader is `_nth()` - a position that holds something else than the constant's
  documented shape yields the default, never a guess. A Google layout change therefore fails LOUD in tests
  (the fixture pins every constant) and EMPTY-but-honest in production (the run's card says the cell yielded
  nothing and the parse-failure tripwire aborts the run) - never quietly wrong.
- IDS BY SHAPE, NOT BY POSITION: kgmid (the `0x...:0x...` feature id - omkarcloud's field doc: place_id can
  null, kgmid never) is scanned among the entry's early strings by SHAPE, because the position moves between
  layouts and the shape does not. place_id (ChIJ...) and cid (the numeric cluster id) sit at their named
  indices with shape checks on top.
- THE STORE BOUNDARY (rules.STORE_BOUNDARY, plan section 8): this parser reads business FACTS ONLY - name,
  category, address, phone, website, rating, review COUNT, coordinates, key ids. Review TEXT, photos, popular
  times and owner PII exist somewhere in the payload and are NEVER READ - not a field below touches them.
  This comment is the rule; a later session cannot "complete" the reader by accident (the v0.389 trap law).
"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote_plus

PARSER_GMAPS = "v0.690.0-gm1"     # every scraped row names this code as the reader of its source

SEARCH_HOST = "www.google.com"
PAGE_SIZE = 20                    # listings per search page (the pb parameter's page step)
PAGES_PER_CELL_MAX = 6            # 6 pages x 20 = 120 listings/cell - the known ~120 ceiling (plan 1.4)

# ---------------------------------------------------------------- the URL builder (one function, one correction)
def search_url(query: str, lat: float, lng: float, zoom: int, page: int = 0, hl: str = "en", gl: str = "in") -> str:
    """The public /maps/search GET for one cell page.

    Shape (the gosom idea, our own builder): the query in the path, the viewport @lat,lng,zoomz, hl/gl locale,
    and pb=!7i20!8i{start+20} paging 20 listings at a time - page 0 -> !8i20, page 1 -> !8i40, page 2 -> !8i60.
    SAMPLE: search_url("dentists", 18.5204, 73.8567, 15, page=1) =
      https://www.google.com/maps/search/dentists/@18.520400,73.856700,15z?hl=en&gl=in&pb=!7i20!8i40
    NOT VERIFIED against the live page until her first run - the plan's named unknown #1. If Google's live
    shape differs, THIS function is the one line that changes and the fixture test re-pins it."""
    start = PAGE_SIZE + PAGE_SIZE * max(0, int(page))
    return (f"https://{SEARCH_HOST}/maps/search/{quote_plus(str(query or '').strip())}"
            f"/@{float(lat):.6f},{float(lng):.6f},{int(zoom)}z?hl={hl}&gl={gl}&pb=!7i{PAGE_SIZE}!8i{start}")


# ---------------------------------------------------------------- the field constants (each with its proof sample)
# Every constant carries the SAMPLE from the recorded fixture (tests/test_v0543_leads_scrape.py) that proves the
# position. A live layout change breaks the fixture's expectations LOUDLY in tests; in production an unknown
# position reads as the default (never a guess) and the run's parse-failure tripwire aborts the run.
IDX_ADDRESS = 2                   # "Shop 4, MG Road, Pune, Maharashtra 411001"
IDX_COORDS = 3                    # [0, 18.5204, 73.8567, ...] - lat at [1], lng at [2]
IDX_RATING = 4                    # 4.5 (float) or absent -> None; FACTS only, never the review text
IDX_WEBSITE = 7                   # "http://www.sharmadental.in"
IDX_PLACE_ID = 9                  # "ChIJN1t_tDeuEmsRUsoyG82frLA" (shape-checked: ChIJ prefix)
IDX_CID = 10                      # 2384729384 (int, the numeric cluster id)
IDX_TITLE = 11                    # "Sharma Dental Clinic"
IDX_CATEGORIES = 14               # ["Dentist", "Dental clinic"]
IDX_PHONE = 178                   # "+91 98765 43210"
IDX_REVIEW_COUNT = 269            # 128 (int) - the COUNT; the review TEXT is never read (STORE_BOUNDARY)
KGMID_RE = re.compile(r"^0x[0-9a-fA-F]+:0x[0-9a-fA-F]+$")       # "0x3bde7c9bcd1234ab:0x5f6e7d8c9b0a1234"
KGMID_SCAN = 20                   # kgmid is scanned among the entry's first KGMID_SCAN strings (shape, not index)
_INIT_MARKER = "window.APP_INITIALIZATION_STATE="

# ---------------------------------------------------------------- the loud tripwire
class GmapsParseError(ValueError):
    """The page is not a Maps search page (block page slipped past, or the layout moved). The runner treats
    this as the LOUD signal - two consecutive cells of it abort the run with the reason, never a quiet empty."""


def _extract_init_state(html: str) -> list:
    """Find `window.APP_INITIALIZATION_STATE=[...]` and decode it with a bracket scanner (string- and
    escape-aware, so a `]` inside a listing title cannot end the scan early). Missing marker or unparseable
    payload -> GmapsParseError (loud), never a silent empty."""
    s = str(html or "")
    i = s.find(_INIT_MARKER)
    if i < 0:
        raise GmapsParseError("APP_INITIALIZATION_STATE nahi mila - page search-result page nahi hai "
                              "(block page ya layout badla).")
    j = s.find("[", i + len(_INIT_MARKER))
    if j < 0:
        raise GmapsParseError("APP_INITIALIZATION_STATE khulta nahi (layout badla).")
    depth, in_str, esc = 0, False, False
    for k in range(j, min(len(s), j + 20_000_000)):
        c = s[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                try:
                    out = json.loads(s[j:k + 1])
                except Exception as e:                        # noqa: BLE001 - loud, with the reason
                    raise GmapsParseError(f"APP_INITIALIZATION_STATE parse nahi hua ({e}) - layout badla.") from None
                if not isinstance(out, list):
                    raise GmapsParseError("APP_INITIALIZATION_STATE array nahi hai - layout badla.")
                return out
    raise GmapsParseError("APP_INITIALIZATION_STATE kabhi band nahi hua (page kat gaya / layout badla).")


def _walk(node: Any, out: list, depth: int) -> None:
    """Depth-first walk of the init state: nested lists are descended, nested JSON-encoded strings are decoded
    once and descended (the payload rides inside string positions in the real layout), and every list that
    PASSES THE SHAPE TEST is read as one listing. Depth-bounded so a pathological page cannot loop us."""
    if depth > 8:
        return
    if isinstance(node, str):
        t = node.strip()
        if t[:1] in ("[", "{"):
            try:
                decoded = json.loads(t)
            except Exception:                                 # noqa: BLE001 - a string that is not JSON is just a string
                return
            _walk(decoded, out, depth + 1)
        return
    if not isinstance(node, list):
        return
    if is_place(node):
        out.append(read_place(node))
        return
    for ch in node:
        _walk(ch, out, depth + 1)


def is_place(a: list) -> bool:
    """The SHAPE TEST a listing array must pass before any index is trusted: long enough to carry the deep
    fields, a string address at IDX_ADDRESS, numeric lat/lng inside IDX_COORDS, a non-empty string title at
    IDX_TITLE. One wrong array type anywhere -> not a listing, no read."""
    return (len(a) > IDX_CATEGORIES
            and isinstance(a[IDX_ADDRESS], str) and bool(a[IDX_ADDRESS])
            and isinstance(a[IDX_COORDS], list) and len(a[IDX_COORDS]) > 2
            and isinstance(a[IDX_COORDS][1], (int, float)) and isinstance(a[IDX_COORDS][2], (int, float))
            and isinstance(a[IDX_TITLE], str) and bool(a[IDX_TITLE]))


def _nth(a: list, idx: int, default: Any) -> Any:
    return a[idx] if isinstance(a, list) and len(a) > idx and a[idx] not in (None, "") else default


def _ids(a: list) -> dict:
    """The identity ids, strongest shape first: kgmid scanned (0x...:0x... - position moves, shape does not),
    place_id at its index (ChIJ shape-checked), cid at its index (positive int shape-checked)."""
    kgmid = ""
    for v in a[:KGMID_SCAN]:
        if isinstance(v, str) and KGMID_RE.match(v.strip()):
            kgmid = v.strip()
            break
    pid = _nth(a, IDX_PLACE_ID, "")
    place_id = str(pid).strip() if isinstance(pid, str) and str(pid).startswith("ChIJ") else ""
    cid_v = _nth(a, IDX_CID, 0)
    cid = str(int(cid_v)) if isinstance(cid_v, int) and not isinstance(cid_v, bool) and cid_v > 0 else ""
    return {"kgmid": kgmid, "place_id": place_id, "cid": cid}


def read_place(a: list) -> dict:
    """One listing array -> the store's business FACTS row (rules.STORE_BOUNDARY). Nothing here reads review
    text, photos, popular times or owner PII - the boundary is the field list itself."""
    coords = a[IDX_COORDS] if isinstance(a[IDX_COORDS], list) else []
    rating = _nth(a, IDX_RATING, None)
    rc = _nth(a, IDX_REVIEW_COUNT, None)
    cats = _nth(a, IDX_CATEGORIES, [])
    row = {"name": str(_nth(a, IDX_TITLE, ""))[:200],
           "address": str(_nth(a, IDX_ADDRESS, "")),
           "lat": float(coords[1]) if isinstance(coords[1], (int, float)) else None,
           "lng": float(coords[2]) if isinstance(coords[2], (int, float)) else None,
           "rating": float(rating) if isinstance(rating, (int, float)) and not isinstance(rating, bool) else None,
           "review_count": int(rc) if isinstance(rc, int) and not isinstance(rc, bool) and rc >= 0 else None,
           "website": str(_nth(a, IDX_WEBSITE, ""))[:300],
           "phone": str(_nth(a, IDX_PHONE, "")),
           "category": ", ".join(str(x) for x in cats if isinstance(x, str))[:120] if isinstance(cats, list) else "",
           "parser_version": PARSER_GMAPS}
    row.update(_ids(a))
    return row


def places(html: str) -> list[dict]:
    """The page -> the listings' FACTS rows, in page order. A page with no marker raises GmapsParseError (the
    loud tripwire); a valid search page with no shape-matching array returns [] honestly (a sparse cell)."""
    init = _extract_init_state(html)
    out: list[dict] = []
    _walk(init, out, 0)
    return out
