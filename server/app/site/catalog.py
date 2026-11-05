"""v0.538 BADA CATALOGUE (web Step 6 part 1 = W8 content at scale + W10 speed of docs/WEB_PLATFORM_PLAN.md; checkpoint
"5,000-product marketplace, load test passed").

Her products / doctors / properties / courses come from HER data - a CSV or Excel file, her Google Sheet, or a dataset
Hoola already holds (a data_fetch, an ERP read) - and become pages BY CODE: no model call per item, so 10,000 items cost
what one does.

  * IMPORT IS TWO TAPS: `preview` reads the file, maps the columns (title / key / price / photo / description / filters -
    her own mapping wins), and says exactly what would happen: new, changed, unchanged, rejected (with the row and the
    reason), thin and duplicate pages. Nothing is written. `apply` (her tap, by the preview's hash) writes it in batches;
    `replace` hides items that are not in the new file (never deletes them). Re-importing the same file changes nothing:
    each item is matched on its key (SKU / ID / code, else the title) and its address never moves once given.
  * QUALITY GATE (Google's scaled-content policy): a page with almost nothing of its own (THIN_WORDS) or the same content
    as another item is still shown to visitors but carries noindex (a duplicate also points its canonical at the
    original) and is left out of the sitemaps - so 10,000 pages can never make the whole site look like spam.
  * PAGES: one page per item (her designed template for that list when the plan has one, else a code-made page with the
    photo, price, details and links to similar items), listing pages of PER_PAGE cards with numbered pages, a filter bar
    (search, the list's filter columns with counts, price range, sort) that works on the static site from one compact
    JSON index per list (assets/catalog/<list>.json, loaded only when she starts filtering), split sitemaps (a sitemap
    index + at most SITEMAP_MAX addresses per file) and a product price + Add to cart where the shop sells it.
  * PHOTOS: a photo column is either the name of a photo she uploaded or an https address. Each address is fetched ONCE
    (public hosts only, image types only, size + pixel caps), resized to 3 widths as AVIF + WebP + JPEG, cached by its
    content hash and re-used by every build; pages get <picture> with width / height (no layout shift) and lazy loading.
"""
from __future__ import annotations

import csv
import hashlib
import html as _html
import io
import json
import logging
import os
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now, session

log = logging.getLogger("santosh.site.catalog")
MAX_ROWS = 50_000
MAX_COLS = 60
MAX_CELL = 5_000
MAX_FILE = 25 * 1024 * 1024
MAX_LISTS = 12
PER_PAGE = 48
SITEMAP_MAX = 45_000                 # Google: 50,000 a file; kept under it
THIN_WORDS = 20
FACETS_MAX = 6
FACET_VALUES_MAX = 60
CARD_WIDTHS = (320, 640, 1024)
IMG_MAX_BYTES = 10 * 1024 * 1024
IMG_MAX_PIXELS = 40_000_000
STATS = {"previews": 0, "applied": 0, "rows": 0, "images_ok": 0, "images_bad": 0}

TITLE = re.compile(r"^(title|name|product|product name|item|item name|naam|doctor|property|course|heading)$", re.I)
KEY = re.compile(r"^(sku|id|code|item code|product id|product code|ref|reference|item id|listing id)$", re.I)
PRICE = re.compile(r"^(price|mrp|rate|selling price|sale price|cost|amount|fees?|rent|daam|keemat|kiraya)( \(.*\))?$", re.I)
IMAGE = re.compile(r"^(image|image url|images?|photo|photo url|img|picture|thumbnail|main image)$", re.I)
DESC = re.compile(r"^(description|details|about|summary|desc|long description|vivaran)$", re.I)
STOCK = re.compile(r"^(stock|qty|quantity|inventory|available)$", re.I)
SELLER = re.compile(r"^(seller|vendor|sold by|seller name|vendor name|dukaan)$", re.I)
URLISH = re.compile(r"^https?://", re.I)


class CatalogError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


class SiteCatalog(Base):
    """One list of a site: how her columns map onto it."""
    __tablename__ = "site_catalog"
    id: Mapped[str] = mapped_column(String(90), primary_key=True)          # site_id|coll
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    coll: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(80), default="")
    item_label: Mapped[str] = mapped_column(String(60), default="")
    spec: Mapped[str] = mapped_column(Text, default="{}")                   # fields / facets / title / key / price / image / desc
    counts: Mapped[str] = mapped_column(Text, default="{}")
    updated: Mapped[Any] = mapped_column(DateTime(timezone=True), default=now)


class SiteCatalogItem(Base):
    __tablename__ = "site_catalog_item"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)          # sha1(site|coll|key)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    coll: Mapped[str] = mapped_column(String(40), index=True)
    key: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    data: Mapped[str] = mapped_column(Text, default="{}")
    img: Mapped[str] = mapped_column(Text, default="")                      # her photo name or an https address
    img_meta: Mapped[str | None] = mapped_column(Text, nullable=True)       # the made sizes (once fetched)
    q: Mapped[str] = mapped_column(String(8), default="ok")                  # ok | thin | dup
    dup_of: Mapped[str] = mapped_column(String(100), default="")
    live: Mapped[int] = mapped_column(Integer, default=1)
    pos: Mapped[int] = mapped_column(Integer, default=0)
    hash: Mapped[str] = mapped_column(String(20), default="")
    updated: Mapped[Any] = mapped_column(DateTime(timezone=True), default=now)


_OK = False


def ensure_tables() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        for t in (SiteCatalog, SiteCatalogItem):
            t.__table__.create(_db._engine, checkfirst=True)
        _OK = True


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def slug(s: Any, n: int = 80) -> str:
    t = re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    return t[:n].strip("-")


def _key_name(h: str, used: set[str]) -> str:
    k = re.sub(r"[^a-z0-9_]+", "_", str(h or "").lower()).strip("_")[:30] or "col"
    if k[0].isdigit():
        k = "c_" + k
    base, i = k, 2
    while k in used or k in ("title", "id", "slug"):
        k = f"{base}_{i}"
        i += 1
    used.add(k)
    return k


def _clean_cell(v: Any) -> str:
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str("" if v is None else v)).strip()
    return t[:MAX_CELL]


# ---------------------------------------------------------------- reading her data
def parse_file(raw: bytes, filename: str = "") -> list[dict[str, str]]:
    """CSV / TSV / Excel (.xlsx) / JSON array -> rows of {header: text}."""
    if len(raw) > MAX_FILE:
        raise CatalogError(f"File {MAX_FILE // (1024 * 1024)} MB se badi hai - hisson mein bhejiye.")
    name = (filename or "").lower()
    if name.endswith(".xlsx") or raw[:4] == b"PK\x03\x04":
        try:
            import openpyxl
        except ImportError:
            raise CatalogError("Excel padhne ke liye server par openpyxl chahiye - CSV bhejiye.")
        try:
            wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        except Exception:
            raise CatalogError("Excel file khul nahi payi.")
        ws = wb.worksheets[0]
        it = ws.iter_rows(values_only=True)
        head = next(it, None)
        if not head:
            return []
        head = [_clean_cell(h) for h in head][:MAX_COLS]
        out = []
        for row in it:
            if len(out) >= MAX_ROWS:
                break
            d = {head[i]: _clean_cell(v) for i, v in enumerate(list(row)[:len(head)]) if head[i]}
            if any(d.values()):
                out.append(d)
        return out
    if name.endswith(".json") or raw.lstrip()[:1] in (b"[", b"{"):
        try:
            data = json.loads(raw.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError):
            raise CatalogError("JSON padha nahi gaya.")
        if isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), [])
        return [{_clean_cell(k)[:80]: _clean_cell(v) for k, v in list(r.items())[:MAX_COLS]}
                for r in data[:MAX_ROWS] if isinstance(r, dict)]
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:20000], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rd = csv.reader(io.StringIO(text), dialect)
    head = next(rd, None)
    if not head:
        return []
    head = [_clean_cell(h)[:80] for h in head][:MAX_COLS]
    out = []
    for row in rd:
        if len(out) >= MAX_ROWS:
            break
        d = {head[i]: _clean_cell(v) for i, v in enumerate(row[:len(head)]) if head[i]}
        if any(d.values()):
            out.append(d)
    return out


def from_sheet(tenant: str, spreadsheet: str, tab: str | None = None) -> list[dict[str, str]]:
    """Her Google Sheet (her own Google login in Hoola), first row = headers."""
    from ..sheets import service as ss
    c, meta = ss.resolve(tenant, spreadsheet)
    t = ss.load(c, meta, tab, 1)
    head = [str(h or "") for h in t.header][:MAX_COLS]
    out = []
    for r in t.rows[:MAX_ROWS]:
        d = {head[i]: _clean_cell(t.cell(r, i)) for i in range(len(head)) if head[i]}
        if any(d.values()):
            out.append(d)
    return out


def from_dataset(tenant: str, ds: str) -> list[dict[str, str]]:
    """A dataset Hoola already holds (data_fetch, her ERP read saved as data) - rows as they are."""
    from .. import datasets as DS
    doc = DS.load(tenant, ds)
    rows = doc.get("rows") or []
    return [{_clean_cell(k)[:80]: _clean_cell(v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False))
             for k, v in list(r.items())[:MAX_COLS]} for r in rows[:MAX_ROWS] if isinstance(r, dict)]


# ---------------------------------------------------------------- what each column means
def num(v: Any) -> float | None:
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(v or ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def guess_mapping(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Which column is the title / key / price / photo / description, which are filters; her own mapping overrides."""
    heads = list(dict.fromkeys(h for r in rows[:200] for h in r))
    n = max(1, min(len(rows), 2000))
    sample = rows[:2000]
    pick = lambda rx: next((h for h in heads if rx.match(h.strip())), "")  # noqa: E731
    m: dict[str, Any] = {"title": pick(TITLE), "key": pick(KEY), "price": pick(PRICE), "image": pick(IMAGE),
                         "description": pick(DESC), "stock": pick(STOCK)}
    if not m["title"]:                                      # the first mostly-filled text column
        for h in heads:
            vals = [r.get(h, "") for r in sample]
            if sum(1 for v in vals if v) >= 0.8 * n and sum(1 for v in vals if num(v) is None) >= 0.8 * n:
                m["title"] = h
                break
    taken = {v for v in m.values() if v}
    facets = []
    for h in heads:
        if h in taken or len(facets) >= FACETS_MAX:
            continue
        vals = [r.get(h, "") for r in sample if r.get(h, "")]
        if len(vals) < 0.5 * n:
            continue
        distinct = set(vals)
        if 2 <= len(distinct) <= FACET_VALUES_MAX and len(distinct) < 0.5 * len(vals) and \
                all(len(v) <= 40 and not URLISH.match(v) for v in distinct):
            facets.append(h)
    m["facets"] = facets
    return m


def _spec(rows: list[dict[str, str]], mapping: dict[str, Any] | None) -> dict[str, Any]:
    g = guess_mapping(rows)
    mp = dict(g)
    for k, v in (mapping or {}).items():
        if k in ("title", "key", "price", "image", "description", "stock") and isinstance(v, str):
            mp[k] = v
        if k == "facets" and isinstance(v, list):
            mp["facets"] = [str(x) for x in v][:FACETS_MAX]
        if k == "skip" and isinstance(v, list):
            mp["skip"] = [str(x) for x in v]
    heads = list(dict.fromkeys(h for r in rows[:200] for h in r))
    for k in ("title", "key", "price", "image", "description", "stock"):
        if mp.get(k) and mp[k] not in heads:
            raise CatalogError(f"Column '{mp[k]}' file mein nahi ({k}).")
    if not mp.get("title"):
        raise CatalogError("Naam / title wala column nahi mila - batayiye kaunsa column naam hai.")
    used: set[str] = set()
    fields = []
    for h in heads:
        if h in (mp["title"], mp.get("key"), mp.get("image")) or h in set(mp.get("skip") or []):
            continue
        kind = "price" if h == mp.get("price") else "long" if h == mp.get("description") else \
            "stock" if h == mp.get("stock") else "facet" if h in mp.get("facets", []) else "text"
        fields.append({"key": _key_name(h, used), "label": h[:60], "src": h, "kind": kind})
    return {"title": mp["title"], "key": mp.get("key") or "", "image": mp.get("image") or "", "fields": fields,
            "facets": [f["key"] for f in fields if f["kind"] == "facet"],
            "price": next((f["key"] for f in fields if f["kind"] == "price"), ""),
            "stock": next((f["key"] for f in fields if f["kind"] == "stock"), ""),
            "desc": next((f["key"] for f in fields if f["kind"] == "long"), "")}


def _sig(title: str, data: dict[str, str], spec: dict[str, Any]) -> str:
    """Content signature for the duplicate check (title + everything said about it, minus the key)."""
    vals = [re.sub(r"\s+", " ", title.lower()).strip()] + sorted(
        re.sub(r"\s+", " ", str(v).lower()).strip() for k, v in data.items() if v and k != spec.get("stock"))
    return hashlib.sha1("|".join(vals).encode()).hexdigest()[:16]


def _words(title: str, data: dict[str, str], spec: dict[str, Any]) -> int:
    txt = " ".join([title] + [v for k, v in data.items() if v and not URLISH.match(v)])
    return len(re.findall(r"\w+", txt))


def _items(rows: list[dict[str, str]], spec: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    good, bad = [], []
    seen_keys: set[str] = set()
    for i, r in enumerate(rows):
        title = re.sub(r"\s+", " ", r.get(spec["title"], "")).strip()[:200]
        if not title:
            bad.append({"row": i + 2, "why": "naam khaali"})
            continue
        key = (r.get(spec["key"], "") if spec["key"] else "").strip()[:160] or title.lower()
        if key in seen_keys:
            bad.append({"row": i + 2, "why": f"yeh key pehle aa chuki: {key[:40]}"})
            continue
        seen_keys.add(key)
        data = {f["key"]: r.get(f["src"], "") for f in spec["fields"]}
        if spec["price"] and data.get(spec["price"]) and num(data[spec["price"]]) is None:
            bad.append({"row": i + 2, "why": f"daam ank nahi: {data[spec['price']][:30]}"})
            continue
        if spec["price"] and data.get(spec["price"]) and (num(data[spec["price"]]) or 0) < 0:
            bad.append({"row": i + 2, "why": "daam minus mein"})
            continue
        img = (r.get(spec["image"], "") if spec["image"] else "").split("|")[0].split(",")[0].strip()[:1000]
        if img and URLISH.match(img) and not img.lower().startswith("https://"):
            img = ""                                        # http photos are not fetched (mixed content, no TLS)
        good.append({"key": key, "title": title, "data": data, "img": img, "pos": i})
    return good, bad


def _id(site_id: str, coll: str, key: str) -> str:
    return hashlib.sha1(f"{site_id}|{coll}|{key}".encode()).hexdigest()[:32]


def _site(tenant: str, ref: str):
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    return r


def _pending_dir(r) -> Path:
    from . import build as B
    d = B.src_dir(r.tenant_id, r.id) / "catalog_pending"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _clean_coll(coll: str) -> str:
    c = slug(coll, 40)
    if not c or c in ("assets", "blog", "shop", "account", "admin", "privacy", "terms", "refund", "disclaimer", "page"):
        raise CatalogError("List ka naam (jaise products / doctors / properties) chahiye.")
    return c


# ---------------------------------------------------------------- step 1: preview (nothing written)
def preview(tenant: str, ref: str, coll: str, rows: list[dict[str, str]], mapping: dict[str, Any] | None = None,
            label: str = "", item_label: str = "", source: str = "file") -> dict[str, Any]:
    ensure_tables()
    r = _site(tenant, ref)
    coll = _clean_coll(coll)
    if not rows:
        raise CatalogError("File mein ek bhi row nahi mili.")
    spec = _spec(rows, mapping)
    good, bad = _items(rows, spec)
    with session() as s:
        n_lists = len(set(s.scalars(select(SiteCatalog.coll).where(SiteCatalog.site_id == r.id)).all()) - {coll})
        have = {x.key: x for x in s.scalars(select(SiteCatalogItem).where(SiteCatalogItem.site_id == r.id,
                                                                          SiteCatalogItem.coll == coll)).all()}
        for x in have.values():
            s.expunge(x)
    if n_lists >= MAX_LISTS:
        raise CatalogError(f"Ek website par {MAX_LISTS} lists tak.")
    new = changed = same = 0
    for it in good:
        old = have.get(it["key"])
        h = _row_hash(it)
        if old is None:
            new += 1
        elif old.hash == h and old.live:
            same += 1
        else:
            changed += 1
    q = quality(good, spec)
    body = {"coll": coll, "label": (label or coll.replace("-", " ").title())[:80], "item_label": (item_label or "")[:60],
            "spec": spec, "items": good, "source": source, "rows": len(rows)}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True)
    h = hashlib.sha256(raw.encode()).hexdigest()[:20]
    (_pending_dir(r) / f"{h}.json").write_text(raw, encoding="utf-8")
    STATS["previews"] += 1
    sample = [{"title": it["title"], "address": f"/{coll}/{slug(it['title'])}/", "price": it["data"].get(spec["price"], "") if spec["price"] else "",
               "photo": bool(it["img"]), **{f["label"]: it["data"].get(f["key"], "") for f in spec["fields"][:6]}} for it in good[:5]]
    return {"hash": h, "coll": coll, "rows": len(rows), "items": len(good), "new": new, "changed": changed, "same": same,
            "hidden_if_replace": sum(1 for k, x in have.items() if x.live and k not in {it["key"] for it in good}),
            "rejected": len(bad), "rejected_rows": bad[:25], "thin": q["thin"], "dup": q["dup"],
            "mapping": {"title": spec["title"], "key": spec["key"] or "(title)", "image": spec["image"],
                        "price": next((f["src"] for f in spec["fields"] if f["key"] == spec["price"]), ""),
                        "filters": [f["src"] for f in spec["fields"] if f["key"] in spec["facets"]],
                        "fields": [f["src"] for f in spec["fields"]]},
            "photos": sum(1 for it in good if it["img"]), "sample": sample,
            "say": f"{len(good)} items taiyaar ({new} naye, {changed} badle, {same} waise hi), {len(bad)} rows chhoote. "
                   "Kuch likha nahi gaya - 'Apply' aapke tap se."}


def _row_hash(it: dict[str, Any]) -> str:
    return hashlib.sha1(json.dumps([it["title"], it["data"], it["img"]], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]


def quality(items: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
    """Marks each item ok / thin / dup in place (dup_of = the first item with the same content); returns counts."""
    first: dict[str, str] = {}
    thin = dup = 0
    for it in sorted(items, key=lambda x: x.get("pos", 0)):
        sg = _sig(it["title"], it["data"], spec)
        if sg in first:
            it["q"], it["dup_of_key"] = "dup", first[sg]
            dup += 1
            continue
        first[sg] = it["key"]
        if _words(it["title"], it["data"], spec) < THIN_WORDS and not it.get("img"):
            it["q"] = "thin"
            thin += 1
        else:
            it["q"] = "ok"
    return {"thin": thin, "dup": dup}


# ---------------------------------------------------------------- step 2: apply (her tap)
def apply(tenant: str, ref: str, h: str, replace: bool = False) -> dict[str, Any]:
    ensure_tables()
    r = _site(tenant, ref)
    if not re.fullmatch(r"[0-9a-f]{20}", str(h or "")):
        raise CatalogError("Preview dobara banaiye.", 409)
    p = _pending_dir(r) / f"{h}.json"
    if not p.exists():
        raise CatalogError("Yeh preview purana ho gaya - file dobara daaliye.", 409)
    body = json.loads(p.read_text(encoding="utf-8"))
    coll, spec, good = body["coll"], body["spec"], body["items"]
    quality(good, spec)
    added = changed = same = hidden = 0
    with session() as s:
        have = {x.key: x for x in s.scalars(select(SiteCatalogItem).where(SiteCatalogItem.site_id == r.id,
                                                                          SiteCatalogItem.coll == coll)).all()}
        used = {x.slug for x in have.values()}
        by_key_slug = {k: x.slug for k, x in have.items()}
        for it in good:                                     # addresses first: an item keeps its address for ever
            if it["key"] not in by_key_slug:
                base = slug(it["title"]) or "item"
                sg, i = base, 2
                while sg in used:
                    sg = f"{base}-{i}"
                    i += 1
                used.add(sg)
                by_key_slug[it["key"]] = sg
        for it in good:
            x = have.get(it["key"])
            hh = _row_hash(it)
            dup_of = by_key_slug.get(it.get("dup_of_key", ""), "") if it.get("q") == "dup" else ""
            if x is None:
                x = SiteCatalogItem(id=_id(r.id, coll, it["key"]), site_id=r.id, coll=coll, key=it["key"],
                                    slug=by_key_slug[it["key"]], title=it["title"])
                s.add(x)
                added += 1
            elif x.hash == hh and x.live and x.q == it["q"] and x.dup_of == dup_of and x.pos == it["pos"]:
                same += 1
                continue
            else:
                changed += 1
            if x.img != it["img"]:
                x.img_meta = None                            # a new photo address = fetched again
            x.title, x.data, x.img, x.hash, x.live = it["title"], json.dumps(it["data"], ensure_ascii=False), it["img"], hh, 1
            x.q, x.dup_of, x.pos, x.updated = it["q"], dup_of, it["pos"], now()
        if replace:
            keep = {it["key"] for it in good}
            for k, x in have.items():
                if k not in keep and x.live:
                    x.live, x.updated = 0, now()
                    hidden += 1
        cid = f"{r.id}|{coll}"
        cat = s.get(SiteCatalog, cid) or SiteCatalog(id=cid, site_id=r.id, coll=coll)
        cat.label, cat.item_label = body["label"], body.get("item_label") or cat.item_label or ""
        cat.spec = json.dumps(spec, ensure_ascii=False)
        cat.updated = now()
        s.merge(cat)
    counts = _count(r.id, coll)
    with session() as s:
        cat = s.get(SiteCatalog, f"{r.id}|{coll}")
        cat.counts = json.dumps(counts)
    p.unlink(missing_ok=True)
    STATS["applied"] += 1
    STATS["rows"] += len(good)
    shop = sync_shop(r, coll)
    if counts.get("photos_todo"):
        start_images(r.id)
    return {"coll": coll, "added": added, "changed": changed, "same": same, "hidden": hidden, **counts, "shop": shop,
            "say": f"{added} naye, {changed} badle, {hidden} chhupe. Website ki nayi version banane par sab pages ban jayenge."}


def _count(site_id: str, coll: str) -> dict[str, int]:
    with session() as s:
        xs = s.execute(select(SiteCatalogItem.live, SiteCatalogItem.q, SiteCatalogItem.img, SiteCatalogItem.img_meta)
                       .where(SiteCatalogItem.site_id == site_id, SiteCatalogItem.coll == coll)).all()
    live = [x for x in xs if x[0]]
    return {"live": len(live), "hidden": len(xs) - len(live), "ok": sum(1 for x in live if x[1] == "ok"),
            "thin": sum(1 for x in live if x[1] == "thin"), "dup": sum(1 for x in live if x[1] == "dup"),
            "photos": sum(1 for x in live if x[3]), "photos_todo": sum(1 for x in live if x[2] and not x[3])}


def sync_shop(r, coll: str) -> dict[str, Any]:
    """Items with a price become her shop's products (slug = the item's address) when her shop is on."""
    from . import service as S
    from . import shop as SH
    try:
        if not S._shop_cfg(r)["on"]:
            return {"on": False}
    except Exception:                                         # noqa: BLE001
        return {"on": False}
    cat = spec_of(r.id, coll)
    if not cat or not cat["spec"].get("price"):
        return {"on": True, "products": 0}
    pk, sk = cat["spec"]["price"], cat["spec"].get("stock") or ""
    items = []
    with session() as s:
        for x in s.scalars(select(SiteCatalogItem).where(SiteCatalogItem.site_id == r.id, SiteCatalogItem.coll == coll)).all():
            d = _j(x.data, {})
            pr = num(d.get(pk))
            if pr is None:
                continue
            it = {"slug": f"{coll}/{x.slug}", "title": x.title, "price": f"{pr:.2f}", "active": bool(x.live)}
            if sk:
                st = num(d.get(sk))
                it["stock"] = None if st is None else max(0, int(st))
            items.append(it)
    got = SH.upsert_products(r.id, items)
    sellers = _sellers(r, coll, cat["spec"])
    return {"on": True, "products": len(items), **got, **({"sellers": sellers} if sellers else {})}


def _sellers(r, coll: str, spec: dict[str, Any]) -> dict[str, int]:
    """v0.538 a marketplace file: a seller column links each product to HER approved seller of that name (an unknown or
    unapproved seller's product stays hers - never handed to someone she did not approve)."""
    sk = next((f["key"] for f in spec.get("fields", []) if SELLER.match(f.get("src") or f.get("label") or "")), "")
    if not sk:
        return {}
    from . import shop as SH
    from . import shopplus as SPL
    SPL.ensure_tables()
    linked = unknown = 0
    with session() as s:
        vs = {v.name.strip().lower(): v.id for v in s.scalars(select(SPL.SiteShopVendor).where(
            SPL.SiteShopVendor.site_id == r.id, SPL.SiteShopVendor.status == "approved")).all()}
        want = {f"{coll}/{x.slug}": str(_j(x.data, {}).get(sk) or "").strip().lower()
                for x in s.scalars(select(SiteCatalogItem).where(SiteCatalogItem.site_id == r.id, SiteCatalogItem.coll == coll)).all()}
        for p in s.scalars(select(SH.SiteShopProduct).where(SH.SiteShopProduct.site_id == r.id,
                                                           SH.SiteShopProduct.slug.in_(list(want)))).all():
            vid = vs.get(want.get(p.slug, ""))
            if vid:
                p.vendor, p.mod = vid, "ok"
                linked += 1
            elif want.get(p.slug):
                unknown += 1
    return {"linked": linked, "unknown_seller": unknown}


def spec_of(site_id: str, coll: str) -> dict[str, Any] | None:
    ensure_tables()
    with session() as s:
        c = s.get(SiteCatalog, f"{site_id}|{coll}")
        if c is None:
            return None
        return {"coll": c.coll, "label": c.label, "item_label": c.item_label, "spec": _j(c.spec, {}), "counts": _j(c.counts, {})}


def lists(tenant: str, ref: str) -> dict[str, Any]:
    ensure_tables()
    r = _site(tenant, ref)
    with session() as s:
        cs = s.scalars(select(SiteCatalog).where(SiteCatalog.site_id == r.id)).all()
        out = [{"coll": c.coll, "label": c.label, "item_label": c.item_label, "counts": _j(c.counts, {}),
                "filters": [f["label"] for f in _j(c.spec, {}).get("fields", []) if f["key"] in _j(c.spec, {}).get("facets", [])],
                "updated": c.updated.isoformat() if c.updated else ""} for c in cs]
    for o in out:
        o["counts"] = _count(r.id, o["coll"])
    return {"lists": out, "images": dict(_IMG_STATE.get(r.id) or {}), "limits": {"rows": MAX_ROWS, "lists": MAX_LISTS,
                                                                                  "per_page": PER_PAGE}}


def remove(tenant: str, ref: str, coll: str) -> dict[str, Any]:
    """Her tap: the list leaves the website (its rows are hidden, never deleted; a re-import brings them back)."""
    ensure_tables()
    r = _site(tenant, ref)
    with session() as s:
        n = 0
        for x in s.scalars(select(SiteCatalogItem).where(SiteCatalogItem.site_id == r.id, SiteCatalogItem.coll == coll)).all():
            if x.live:
                x.live = 0
                n += 1
        c = s.get(SiteCatalog, f"{r.id}|{coll}")
        if c is not None:
            s.delete(c)
    return {"hidden": n, "say": f"List hata di ({n} pages); agli version mein nahi dikhegi."}


# ---------------------------------------------------------------- photos: fetched once, resized once
_IMG_STATE: dict[str, dict[str, Any]] = {}
_IMG_LOCK = threading.Lock()
_FETCH = None                                                 # tests: a fake fetcher(url) -> bytes


def _img_cache(site_id: str) -> Path:
    from . import build as B
    from .models import Site
    with session() as s:
        r = s.get(Site, site_id)
        tenant = r.tenant_id if r else "x"
    d = B.src_dir(tenant, site_id) / "catalog_img"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fetch(url: str) -> bytes:
    if _FETCH is not None:
        return _FETCH(url)
    import httpx
    from urllib.parse import urlparse
    from ..appmaker import connect as CN
    u = urlparse(url)
    if u.scheme != "https" or not u.hostname or u.username or u.port not in (None, 443):
        raise CatalogError("sirf https photo")
    CN._guard_host(u.hostname.lower())                       # never Hoola's own network / a private address
    with httpx.Client(timeout=15.0, follow_redirects=False, headers={"User-Agent": "HoolaCatalog/1.0"}) as c:
        with c.stream("GET", url) as resp:
            if resp.status_code != 200 or not resp.headers.get("content-type", "").startswith("image/"):
                raise CatalogError(f"photo {resp.status_code}")
            buf = bytearray()
            for chunk in resp.iter_bytes():
                buf.extend(chunk)
                if len(buf) > IMG_MAX_BYTES:
                    raise CatalogError("photo bahut badi")
            return bytes(buf)


def one_image(site_id: str, item_id: str, photos: dict[str, Path] | None = None) -> bool:
    from PIL import Image
    from . import build as B
    with session() as s:
        x = s.get(SiteCatalogItem, item_id)
        if x is None or not x.img or x.img_meta:
            return False
        src_ref = x.img
    cache = _img_cache(site_id)
    try:
        if URLISH.match(src_ref):
            raw = _fetch(src_ref)
        else:                                                # one of her uploaded site photos, by name
            p = (photos or {}).get(src_ref)
            if p is None or not Path(p).exists():
                raise CatalogError("photo naam nahi mila")
            raw = Path(p).read_bytes()
        Image.MAX_IMAGE_PIXELS = IMG_MAX_PIXELS
        im = Image.open(io.BytesIO(raw))
        im.verify()
        hsh = hashlib.sha256(raw).hexdigest()[:16]
        name = f"c-{hsh}"
        stamp = cache / f"{name}.json"
        if stamp.exists():
            meta = json.loads(stamp.read_text())
        else:
            src = cache / f"{name}.src"
            src.write_bytes(raw)
            meta = B.photo_set(src, name, cache, widths=CARD_WIDTHS)
            src.unlink(missing_ok=True)
            stamp.write_text(json.dumps(meta))
        ok = True
    except Exception as e:                                   # noqa: BLE001 - a bad photo never stops the others
        meta, ok = {"bad": str(e)[:80]}, False
    with session() as s:
        x = s.get(SiteCatalogItem, item_id)
        if x is not None:
            x.img_meta = json.dumps(meta)
    STATS["images_ok" if ok else "images_bad"] += 1
    return ok


def images(site_id: str, limit: int = 20_000, workers: int = 6) -> dict[str, int]:
    """Every live item whose photo was never made: fetched + resized (6 at a time). Safe to run again (resumes)."""
    ensure_tables()
    with _IMG_LOCK:
        lk = _SITE_LOCKS.setdefault(site_id, threading.Lock())
    with lk:                                                 # one photo run per site at a time (a double tap waits, then finds 0)
        return _images(site_id, limit, workers)


_SITE_LOCKS: dict[str, threading.Lock] = {}


def _images(site_id: str, limit: int, workers: int) -> dict[str, int]:
    from .models import Site
    from . import build as B
    with session() as s:
        ids = s.scalars(select(SiteCatalogItem.id).where(SiteCatalogItem.site_id == site_id, SiteCatalogItem.live == 1,
                                                        SiteCatalogItem.img != "", SiteCatalogItem.img_meta.is_(None))
                        .limit(limit)).all()
        r = s.get(Site, site_id)
        photos = {p["name"]: B.src_dir(r.tenant_id, r.id) / p.get("file", p["name"]) for p in _j(r.photos, [])} if r else {}
    st = {"todo": len(ids), "done": 0, "ok": 0, "bad": 0, "running": True, "at": time.time()}
    _IMG_STATE[site_id] = st
    with ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="cat-img") as ex:
        for ok in ex.map(lambda i: one_image(site_id, i, photos), ids):
            st["done"] += 1
            st["ok" if ok else "bad"] += 1
    st["running"] = False
    return {k: v for k, v in st.items() if k != "at"}


def start_images(site_id: str) -> None:
    with _IMG_LOCK:
        if (_IMG_STATE.get(site_id) or {}).get("running"):
            return
        _IMG_STATE[site_id] = {"running": True, "todo": 0, "done": 0, "ok": 0, "bad": 0}
    threading.Thread(target=lambda: _safe(images, site_id), name="cat-img", daemon=True).start()


def _safe(fn, *a):
    try:
        fn(*a)
    except Exception:                                         # noqa: BLE001
        log.exception("catalog images")
        st = _IMG_STATE.get(a[0])
        if st:
            st["running"] = False


# ---------------------------------------------------------------- the build: pages, listings, filter index, sitemaps
def load(site_id: str) -> list[dict[str, Any]]:
    """Every list of the site with its live items (for the build), in her file's order."""
    if not site_id:
        return []
    ensure_tables()
    with session() as s:
        cats = s.scalars(select(SiteCatalog).where(SiteCatalog.site_id == site_id).order_by(SiteCatalog.coll)).all()
        out = []
        for c in cats:
            spec = _j(c.spec, {})
            rows = s.execute(select(SiteCatalogItem.slug, SiteCatalogItem.title, SiteCatalogItem.data, SiteCatalogItem.img_meta,
                                    SiteCatalogItem.q, SiteCatalogItem.dup_of, SiteCatalogItem.updated)
                             .where(SiteCatalogItem.site_id == site_id, SiteCatalogItem.coll == c.coll, SiteCatalogItem.live == 1)
                             .order_by(SiteCatalogItem.pos, SiteCatalogItem.slug)).all()
            items = []
            for sg, title, data, meta, q, dup_of, upd in rows:
                m = _j(meta, None)
                items.append({"slug": sg, "title": title, "data": _j(data, {}), "img": m if m and m.get("sizes") else None,
                              "q": q, "dup_of": dup_of, "updated": upd.date().isoformat() if upd else ""})
            out.append({"key": c.coll, "label": c.label or c.coll, "item_label": c.item_label or "", "spec": spec,
                        "fields": [{"key": f["key"], "label": f["label"]} for f in spec.get("fields", [])], "items": items})
    return out


def _e(s: Any) -> str:
    return _html.escape(str(s or ""), quote=True)


def price_text(v: Any) -> str:
    n = num(v)
    if n is None:
        return ""
    whole = int(n)
    s = str(whole)
    if len(s) > 3:                                           # Indian grouping 1,23,456
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
        s = f"{head},{tail}"
    paise = round((n - whole) * 100)
    return f"₹{s}" + (f".{paise:02d}" if paise else "")


def card_picture(meta: dict[str, Any] | None, alt: str, rel: str, eager: bool = False, sizes: str = "(max-width:600px) 50vw, 320px") -> str:
    if not meta or not meta.get("sizes"):
        return ""
    from . import build as B
    return B.picture(meta, alt, rel, eager=eager, cls="hs-cat-img", sizes=sizes)


def _facets(c: dict[str, Any]) -> list[dict[str, Any]]:
    spec = c["spec"]
    out = []
    for fk in spec.get("facets", []):
        label = next((f["label"] for f in spec.get("fields", []) if f["key"] == fk), fk)
        counts: dict[str, int] = {}
        for it in c["items"]:
            v = str(it["data"].get(fk) or "").strip()
            if v:
                counts[v] = counts.get(v, 0) + 1
        vals = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:FACET_VALUES_MAX]
        out.append({"key": fk, "label": label, "values": vals})
    return out


def index_json(c: dict[str, Any], rel_img: str = "") -> str:
    """The compact filter index: one row per item [slug, title, price, price_text, photo-320, [facet value indexes]]."""
    spec = c["spec"]
    fac = _facets(c)
    pos = [{v: i for i, (v, _n) in enumerate(f["values"])} for f in fac]
    rows = []
    for it in c["items"]:
        pr = num(it["data"].get(spec.get("price"))) if spec.get("price") else None
        img = ""
        if it.get("img"):
            w = it["img"]["sizes"][0][0]
            img = f'{it["img"]["name"]}-{w}.webp'
        fv = [pos[i].get(str(it["data"].get(f["key"]) or "").strip(), -1) for i, f in enumerate(fac)]
        rows.append([it["slug"], it["title"], pr, price_text(pr) if pr is not None else "", img, fv])
    return json.dumps({"v": 1, "coll": c["key"], "per": PER_PAGE,
                       "facets": [{"key": f["key"], "label": f["label"], "values": [v for v, _n in f["values"]]} for f in fac],
                       "items": rows}, ensure_ascii=False, separators=(",", ":"))


def card(c: dict[str, Any], it: dict[str, Any], rel: str, eager: bool = False) -> str:
    spec = c["spec"]
    pr = it["data"].get(spec.get("price")) if spec.get("price") else ""
    sub = next((str(it["data"].get(fk) or "") for fk in spec.get("facets", []) if it["data"].get(fk)), "")
    return (f'<li class="hs-cat-card"><a href="{rel}{c["key"]}/{it["slug"]}/">'
            + card_picture(it.get("img"), it["title"], rel, eager)
            + f'<span class="hs-cat-t">{_e(it["title"])}</span>'
            + (f'<span class="hs-cat-p">{_e(price_text(pr))}</span>' if price_text(pr) else "")
            + (f'<span class="hs-cat-s">{_e(sub)}</span>' if sub else "") + "</a></li>")


def pages_count(c: dict[str, Any]) -> int:
    return max(1, -(-len(c["items"]) // PER_PAGE))


def page_slug(c: dict[str, Any], n: int) -> str:
    return c["key"] if n == 1 else f'{c["key"]}/page/{n}'


def pager(c: dict[str, Any], n: int, rel: str) -> str:
    total = pages_count(c)
    if total == 1:
        return ""
    root = rel                                               # rel already climbs to the site root
    nums = sorted({1, total, *range(max(1, n - 2), min(total, n + 2) + 1)})
    parts, last = [], 0
    for k in nums:
        if k - last > 1:
            parts.append('<li class="hs-pg-gap" aria-hidden="true">…</li>')
        href = f'{root}{page_slug(c, k)}/'
        parts.append(f'<li><a href="{href}"' + (' aria-current="page"' if k == n else "") + f'>{k}</a></li>')
        last = k
    prev = f'<a class="hs-pg-prev" rel="prev" href="{root}{page_slug(c, n - 1)}/">Previous</a>' if n > 1 else ""
    nxt = f'<a class="hs-pg-next" rel="next" href="{root}{page_slug(c, n + 1)}/">Next</a>' if n < total else ""
    return f'<nav class="hs-pager" aria-label="Pages">{prev}<ol>{"".join(parts)}</ol>{nxt}</nav>'


def filter_bar(c: dict[str, Any], rel: str) -> str:
    """The filter form (her filter columns + search + price + sort). Works once the visitor touches it (the index loads then)."""
    fac = _facets(c)
    sels = "".join(
        f'<label><span>{_e(f["label"])}</span><select name="{_e(f["key"])}"><option value="">All</option>'
        + "".join(f'<option value="{_e(v)}">{_e(v)} ({n})</option>' for v, n in f["values"]) + "</select></label>"
        for f in fac if len(f["values"]) > 1)
    price = ('<label><span>Min ₹</span><input name="pmin" inputmode="numeric" size="6"></label>'
             '<label><span>Max ₹</span><input name="pmax" inputmode="numeric" size="6"></label>') if c["spec"].get("price") else ""
    sort = ('<label><span>Sort</span><select name="sort"><option value="">Featured</option><option value="az">Name A-Z</option>'
            + ('<option value="lo">Price: low to high</option><option value="hi">Price: high to low</option>' if c["spec"].get("price") else "")
            + "</select></label>")
    return (f'<form class="hs-cat-filter" role="search" data-hoola-catalog="{rel}assets/catalog/{_e(c["key"])}.json" '
            f'data-root="{rel}" aria-label="Filter {_e(c["label"])}">'
            f'<label class="hs-cat-q"><span>Search</span><input type="search" name="q" placeholder="Search {len(c["items"])} {_e(c["label"]).lower()}"></label>'
            f'{sels}{price}{sort}<button type="reset" class="btn btn-ghost">Clear</button></form>'
            '<p class="hs-cat-count muted" aria-live="polite"></p>')


def listing(c: dict[str, Any], n: int, rel: str) -> str:
    items = c["items"][(n - 1) * PER_PAGE: n * PER_PAGE]
    return (f'<section class="hs hs-cat" aria-label="{_e(c["label"])}"><div class="wrap">'
            + (filter_bar(c, rel) if n == 1 else "")
            + f'<ul class="hs-cat-grid" data-count="{len(c["items"])}">'
            + "".join(card(c, it, rel, eager=(n == 1 and i < 2)) for i, it in enumerate(items))
            + "</ul>" + pager(c, n, rel) + "</div></section>")


def listing_head(c: dict[str, Any], n: int) -> str:
    return (f'<section class="hs hs-page-head"><div class="wrap"><h1>{_e(c["label"])}' + (f' <small>page {n}</small>' if n > 1 else "")
            + f'</h1><p class="lead">{len(c["items"])} {_e((c["item_label"] or c["label"]).lower())}</p></div></section>')


def related(c: dict[str, Any], it: dict[str, Any], by_facet: dict[tuple[str, str], list[int]], idx: int, rel: str) -> str:
    """Up to 6 items sharing her first filter value (links between pages; never random)."""
    spec = c["spec"]
    for fk in spec.get("facets", []):
        v = str(it["data"].get(fk) or "").strip()
        if not v:
            continue
        pool = by_facet.get((fk, v)) or []
        if len(pool) < 2:
            continue
        k = pool.index(idx) if idx in pool else 0
        pick = [pool[(k + j) % len(pool)] for j in range(1, min(7, len(pool)))]
        lab = next((f["label"] for f in spec.get("fields", []) if f["key"] == fk), fk)
        return (f'<section class="hs hs-cat-rel" aria-label="More"><div class="wrap"><h2>More: {_e(lab)} {_e(v)}</h2>'
                f'<ul class="hs-cat-grid">' + "".join(card(c, c["items"][j], rel) for j in pick) + "</ul></div></section>")
    return ""


def item_body(c: dict[str, Any], it: dict[str, Any], rel: str) -> str:
    """The code-made item page (when her plan has no designed template for this list)."""
    spec = c["spec"]
    pr = it["data"].get(spec.get("price")) if spec.get("price") else ""
    desc = it["data"].get(spec.get("desc")) if spec.get("desc") else ""
    rows = "".join(f'<div><dt>{_e(f["label"])}</dt><dd>{_e(it["data"].get(f["key"]))}</dd></div>'
                   for f in spec.get("fields", []) if f["key"] not in (spec.get("price"), spec.get("desc"), spec.get("stock"))
                   and it["data"].get(f["key"]) and not URLISH.match(str(it["data"].get(f["key"]))))
    return (f'<section class="hs hs-cat-item"><div class="wrap hs-cat-item-grid">'
            + (f'<div class="hs-cat-photo">{card_picture(it.get("img"), it["title"], rel, eager=True, sizes="(max-width:800px) 100vw, 50vw")}</div>'
               if it.get("img") else "")
            + f'<div class="hs-cat-info"><h1>{_e(it["title"])}</h1>'
            + (f'<p class="hs-price">{_e(price_text(pr))}</p>' if price_text(pr) else "")
            + (f'<p class="lead">{_e(desc)}</p>' if desc else "")
            + (f'<dl class="hs-cat-facts">{rows}</dl>' if rows else "")
            + f'<p><a href="{rel}{c["key"]}/">← All {_e(c["label"]).lower()}</a></p></div></div></section>')


def item_desc(c: dict[str, Any], it: dict[str, Any]) -> str:
    spec = c["spec"]
    parts = [str(it["data"].get(spec["desc"]) or "")] if spec.get("desc") else []
    parts += [str(it["data"].get(k) or "") for k in spec.get("facets", [])]
    if spec.get("price") and price_text(it["data"].get(spec["price"])):
        parts.append(price_text(it["data"].get(spec["price"])))
    return re.sub(r"\s+", " ", " · ".join(p for p in parts if p))[:155]


def _link(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy(src, dst)


def write(out: Path, site: dict[str, Any], plan: dict[str, Any], cats: list[dict[str, Any]], render_page, base_url: str,
          designed: set[str], template_render) -> dict[str, Any]:
    """Every catalogue page of the build. render_page(page_dict, body, rel) -> full html; template_render(c, item, rel) ->
    the designed template's body or ''. Returns {pages, urls: [(url, lastmod)] (indexable only), photos}."""
    from . import build as B
    pages = 0
    urls: list[tuple[str, str]] = []
    noindex = 0
    cache_dirs: dict[str, Path] = {}
    img_out = out / "assets" / "img"
    img_out.mkdir(parents=True, exist_ok=True)
    (out / "assets" / "catalog").mkdir(parents=True, exist_ok=True)
    site_id = site.get("site_id") or ""
    for c in cats:
        if not c["items"]:
            continue
        cache = cache_dirs.setdefault(site_id, _img_cache(site_id)) if site_id else None
        for it in c["items"]:                                # photos: hard links from the per-site cache (made once)
            m = it.get("img")
            if m and cache is not None:
                for w, _ww, _hh in m["sizes"]:
                    for ext in ("jpg", "webp", "avif"):
                        f = cache / f'{m["name"]}-{w}.{ext}'
                        if f.exists():
                            _link(f, img_out / f.name)
        (out / "assets" / "catalog" / f'{c["key"]}.json').write_text(index_json(c), encoding="utf-8")
        by_facet: dict[tuple[str, str], list[int]] = {}
        for i, it in enumerate(c["items"]):
            for fk in c["spec"].get("facets", [])[:1]:
                v = str(it["data"].get(fk) or "").strip()
                if v:
                    by_facet.setdefault((fk, v), []).append(i)
        shop_p = {p["slug"]: p for p in (site.get("shop") or {}).get("products") or []}
        for n in range(1, pages_count(c) + 1):               # listing pages
            sg = page_slug(c, n)
            if n == 1 and c["key"] in designed:
                continue                                     # her designed page for this list carries page 1 (build.py)
            rel = B.rel_of(sg)
            page = {"slug": sg, "title": c["label"] + (f" - page {n}" if n > 1 else ""), "nav": "", "parent": "" if n == 1 else c["key"],
                    "description": f'{len(c["items"])} {c["label"].lower()}' + (f", page {n}" if n > 1 else "")}
            body = listing_head(c, n) + listing(c, n, rel)
            _write(out, sg, render_page(page, body, rel))
            pages += 1
            if base_url:
                urls.append((base_url.rstrip("/") + "/" + sg + "/", ""))
        for i, it in enumerate(c["items"]):                  # one page per item
            sg = f'{c["key"]}/{it["slug"]}'
            rel = B.rel_of(sg)
            page = {"slug": sg, "title": it["title"], "nav": "", "parent": c["key"], "description": item_desc(c, it),
                    "collection": c["key"]}
            if it["q"] != "ok":
                page["robots"] = "noindex,follow"
                noindex += 1
            if it["q"] == "dup" and it.get("dup_of") and base_url:
                page["canonical"] = base_url.rstrip("/") + f'/{c["key"]}/{it["dup_of"]}/'
            body = template_render(c, it, rel) or item_body(c, it, rel)
            p = shop_p.get(sg)
            if p:
                body += B.buy_box_of(p)
            body += related(c, it, by_facet, i, rel)
            _write(out, sg, render_page(page, body, rel))
            pages += 1
            if base_url and it["q"] == "ok":
                urls.append((base_url.rstrip("/") + "/" + sg + "/", it.get("updated") or ""))
    return {"pages": pages, "urls": urls, "noindex": noindex}


def _write(out: Path, sg: str, html_text: str) -> None:
    d = out / sg
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_text, encoding="utf-8")


def sitemaps(out: Path, base_url: str, main_urls: list[str], cat_urls: dict[str, list[tuple[str, str]]]) -> list[str]:
    """sitemap.xml = an index; sitemap-pages.xml + sitemap-<list>-<n>.xml, each under SITEMAP_MAX addresses."""
    base = base_url.rstrip("/")
    files = []

    def urlset(rows: list[tuple[str, str]]) -> str:
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                + "".join(f"<url><loc>{_e(u)}</loc>" + (f"<lastmod>{lm}</lastmod>" if lm else "") + "</url>" for u, lm in rows)
                + "</urlset>")
    (out / "sitemap-pages.xml").write_text(urlset([(u, "") for u in main_urls]), encoding="utf-8")
    files.append("sitemap-pages.xml")
    for coll, rows in cat_urls.items():
        for k in range(0, max(1, len(rows)), SITEMAP_MAX):
            chunk = rows[k:k + SITEMAP_MAX]
            if not chunk:
                continue
            fn = f"sitemap-{coll}-{k // SITEMAP_MAX + 1}.xml"
            (out / fn).write_text(urlset(chunk), encoding="utf-8")
            files.append(fn)
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<sitemap><loc>{_e(base)}/{fn}</loc></sitemap>" for fn in files) + "</sitemapindex>", encoding="utf-8")
    return files
