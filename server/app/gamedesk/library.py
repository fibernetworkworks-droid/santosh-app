"""v0.811 GAME TOOL HUB wave 1 (docs/GAME_TOOL_HUB_PLAN.md section 4): FREE 3D models and textures for her games from
three libraries whose own licence allows it, each through its official route only.

- kenney    : 53 low-poly models (platformer, city, shooter, racing pieces) shipped ON Hoola's disk. They come from
              Kenney's own GitHub starter kits, whose READMEs state the models are CC0; no download from kenney.nl is
              automated (the site has no API). Instant, no network.
- polyhaven : Poly Haven's public API (api.polyhaven.com, no key): models (glTF + textures, packed here into one GLB)
              and textures (the 1k colour map). Assets are CC0; the API asks for a unique User-Agent, sent on every call.
- ambientcg : ambientCG's public API v2: materials (the 1K colour map out of the material's zip). Assets are CC0.

`search` only reads; `add` downloads ONE item, checks it by its bytes, and stores it as a DRAFT asset of her Studio
project exactly like her own upload - it enters the game only after her OK (assets.approve), like every asset.
Nothing here costs money, and nothing here is AI-made: the source and licence ride in the asset's history, the
provenance page lists these as library assets made by people, and the game's AI credit line is not triggered by them.

Hosts are a fixed allowlist (redirects too); every download has a byte ceiling; a library that is down is said so."""
from __future__ import annotations

import io
import json
import logging
import re
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import glbpack

log = logging.getLogger("santosh.gamedesk")

UA = "HoolaGameDesk/1.0 (game asset library; https://hoola.ainewtika.com)"
HOSTS = {"api.polyhaven.com", "dl.polyhaven.org", "ambientcg.com", "acg-download.struffelproductions.com"}
MAX_MODEL = 12 * 1024 * 1024            # all the files of one model, before packing
MAX_ZIP = 48 * 1024 * 1024              # one ambientCG 1K-JPG material zip
MAX_IMAGE = 6 * 1024 * 1024
KINDS = ("model", "texture")
SOURCES = {
    "kenney": {"name": "Kenney", "kinds": ("model",), "licence": "CC0 1.0", "credit": "Kenney (kenney.nl)",
               "where": "on Hoola's disk (from Kenney's GitHub starter kits)", "site": "https://kenney.nl"},
    "polyhaven": {"name": "Poly Haven", "kinds": ("model", "texture"), "licence": "CC0 1.0", "credit": "Poly Haven (polyhaven.com)",
                  "where": "Poly Haven's public API", "site": "https://polyhaven.com"},
    "ambientcg": {"name": "ambientCG", "kinds": ("texture",), "licence": "CC0 1.0", "credit": "ambientCG (ambientcg.com)",
                  "where": "ambientCG's public API", "site": "https://ambientcg.com"},
}
_DIR = Path(__file__).parent / "library"
_CACHE: dict[str, tuple[float, Any]] = {}
CACHE_S = 6 * 3600


class LibraryError(Exception):
    pass


# ---------------------------------------------------------------- the one network door
def _fetch(url: str, limit: int, timeout: float = 40.0) -> bytes:
    """GET from an allowlisted host (every redirect hop checked), never more than `limit` bytes."""
    import httpx
    for _hop in range(4):
        u = urlparse(url)
        if u.scheme != "https" or (u.hostname or "") not in HOSTS:
            raise LibraryError(f"not a library address: {u.hostname or url[:60]}")
        with httpx.Client(timeout=timeout, follow_redirects=False, headers={"User-Agent": UA}) as c:
            with c.stream("GET", url) as r:
                if r.status_code in (301, 302, 303, 307, 308):
                    url = str(httpx.URL(url).join(r.headers.get("location", "")))
                    continue
                if r.status_code != 200:
                    raise LibraryError(f"the library answered {r.status_code}")
                out = bytearray()
                for chunk in r.iter_bytes():
                    out += chunk
                    if len(out) > limit:
                        raise LibraryError(f"the file is over {limit // (1024 * 1024)} MB; too big for a game")
                return bytes(out)
    raise LibraryError("too many redirects")


def _json(url: str, cache: str = "") -> Any:
    hit = _CACHE.get(cache) if cache else None
    if hit and time.time() - hit[0] < CACHE_S:
        return hit[1]
    try:
        data = json.loads(_fetch(url, 8 * 1024 * 1024))
    except ValueError:
        raise LibraryError("the library's answer could not be read") from None
    if cache:
        _CACHE[cache] = (time.time(), data)
    return data


# ---------------------------------------------------------------- search
def _words(q: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", (q or "").lower()) if len(w) > 1][:8]


def _score(words: list[str], name: str, tags: list[str]) -> int:
    hay_name = name.lower()
    hay_tags = {t.lower() for t in tags}
    s = 0
    for w in words:
        if w in hay_tags or w in hay_name.split():
            s += 3
        elif w in hay_name or any(w in t for t in hay_tags):
            s += 1
    return s


def kenney_index() -> list[dict[str, Any]]:
    hit = _CACHE.get("kenney")
    if hit:
        return hit[1]
    try:
        rows = json.loads((_DIR / "kenney" / "index.json").read_text(encoding="utf-8"))["items"]
    except Exception:                                   # noqa: BLE001
        log.exception("kenney library index")
        rows = []
    _CACHE["kenney"] = (time.time(), rows)
    return rows


def _item(source: str, iid: str, name: str, kind: str, tags: list[str], **more) -> dict[str, Any]:
    s = SOURCES[source]
    return {"source": source, "source_name": s["name"], "id": iid, "name": name, "kind": kind,
            "tags": sorted({str(t) for t in tags if t})[:10], "licence": s["licence"], "credit": s["credit"], "free": True, **more}


def search(q: str = "", kind: str = "model", source: str = "", limit: int = 24) -> dict[str, Any]:
    """Free library items for her words. kind = model | texture. A library that cannot be reached is named in
    `down`, and the others still answer."""
    if kind not in KINDS:
        raise LibraryError("kind = model | texture")
    if source and source not in SOURCES:
        raise LibraryError("source = " + " | ".join(SOURCES))
    words = _words(q)
    limit = max(1, min(60, int(limit or 24)))
    out: list[tuple[int, dict]] = []
    down: list[str] = []
    for src in ([source] if source else list(SOURCES)):
        if kind not in SOURCES[src]["kinds"]:
            continue
        try:
            if src == "kenney":
                for r in kenney_index():
                    sc = _score(words, r["name"], r.get("tags") or [])
                    if sc or not words:
                        out.append((sc + 1, _item(src, r["id"], r["name"], "model", r.get("tags") or [], kb=r.get("kb"),
                                                  triangles=r.get("triangles"), animations=r.get("animations"), kit=r.get("kit"))))
            elif src == "polyhaven":
                t = "models" if kind == "model" else "textures"
                for iid, a in (_json(f"https://api.polyhaven.com/assets?t={t}", f"ph:{t}") or {}).items():
                    tags = list(a.get("tags") or []) + list(a.get("categories") or [])
                    sc = _score(words, str(a.get("name") or iid), tags)
                    if sc or not words:
                        out.append((sc, _item(src, iid, str(a.get("name") or iid), kind, tags)))
            elif src == "ambientcg":
                if not words:
                    continue                            # ambientCG is searched, never listed whole
                d = _json("https://ambientcg.com/api/v2/full_json?type=Material&limit=30&include=tagData&q=" +
                          "+".join(words), f"acg:{'+'.join(words)}")
                for a in (d or {}).get("foundAssets") or []:
                    tags = list(a.get("tags") or [])
                    out.append((_score(words, str(a.get("assetId") or ""), tags) or 1,
                                _item(src, str(a.get("assetId")), str(a.get("displayName") or a.get("assetId")), "texture", tags)))
        except LibraryError as e:
            down.append(f"{SOURCES[src]['name']}: {e}")
        except Exception as e:                          # noqa: BLE001
            log.exception("library search %s", src)
            down.append(f"{SOURCES[src]['name']}: could not be reached ({type(e).__name__})")
    out.sort(key=lambda x: (-x[0], x[1]["source"] != "kenney", x[1]["name"]))
    return {"q": q, "kind": kind, "items": [i for _s, i in out[:limit]], "found": len(out), "down": down,
            "sources": {k: {"name": v["name"], "licence": v["licence"], "kinds": list(v["kinds"]), "where": v["where"]}
                        for k, v in SOURCES.items()},
            "note": "Free for any use (CC0). An item you add is a draft until you approve it."}


# ---------------------------------------------------------------- one item -> bytes
ID = re.compile(r"^[A-Za-z0-9_\-]{1,80}$")


def _kenney(iid: str) -> tuple[bytes, dict]:
    row = next((r for r in kenney_index() if r["id"] == iid), None)
    if row is None:
        raise LibraryError("no such Kenney model")
    p = _DIR / "kenney" / f"{iid}.glb"
    if not p.is_file():
        raise LibraryError("this Kenney model is not on the server's disk")
    return p.read_bytes(), {"item": iid, "name": row["name"], "from": row.get("from") or SOURCES["kenney"]["site"]}


def _polyhaven_model(iid: str) -> tuple[bytes, dict]:
    files = _json(f"https://api.polyhaven.com/files/{iid}")
    g = (((files or {}).get("gltf") or {}).get("1k") or {}).get("gltf") or {}
    url, inc = g.get("url"), g.get("include") or {}
    if not url:
        raise LibraryError("Poly Haven has no 1k glTF for this item")
    total = int(g.get("size") or 0) + sum(int((v or {}).get("size") or 0) for v in inc.values())
    if total > MAX_MODEL:
        raise LibraryError(f"this model is {total // (1024 * 1024)} MB; too big for a web game (the limit is {MAX_MODEL // (1024 * 1024)} MB)")
    doc = _fetch(url, 2 * 1024 * 1024)
    got: dict[str, bytes] = {}

    def give(uri: str) -> bytes | None:
        key = uri.replace("\\", "/").lstrip("./")
        if key not in inc:
            return None                                 # only what Poly Haven itself lists beside the model
        if key not in got:
            got[key] = _fetch(str(inc[key].get("url")), MAX_MODEL)
        return got[key]
    try:
        glb = glbpack.pack(doc, give)
    except glbpack.PackError as e:
        raise LibraryError(f"the model could not be packed into one file: {e}") from None
    return glb, {"item": iid, "from": f"https://polyhaven.com/a/{iid}", "resolution": "1k"}


def _polyhaven_texture(iid: str) -> tuple[bytes, dict]:
    files = _json(f"https://api.polyhaven.com/files/{iid}")
    d = (files or {}).get("Diffuse") or (files or {}).get("diffuse") or {}
    j = ((d.get("1k") or {}).get("jpg") or {})
    if not j.get("url"):
        raise LibraryError("Poly Haven has no 1k colour map for this item")
    return _fetch(str(j["url"]), MAX_IMAGE), {"item": iid, "from": f"https://polyhaven.com/a/{iid}", "map": "colour, 1k"}


def _ambientcg_texture(iid: str) -> tuple[bytes, dict]:
    d = _json(f"https://ambientcg.com/api/v2/full_json?type=Material&include=downloadData&id={iid}")
    found = (d or {}).get("foundAssets") or []
    if not found:
        raise LibraryError("ambientCG has no such material")
    try:
        dls = found[0]["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"]
    except (KeyError, TypeError):
        raise LibraryError("ambientCG gave no download for this material") from None
    one = next((x for x in dls if x.get("attribute") == "1K-JPG"), None)
    if one is None:
        raise LibraryError("ambientCG has no 1K-JPG for this material")
    if int(one.get("size") or 0) > MAX_ZIP:
        raise LibraryError("this material's download is too big")
    raw = _fetch(str(one.get("downloadLink")), MAX_ZIP, timeout=90.0)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            name = next((n for n in z.namelist() if re.search(r"_Color\.(jpg|jpeg|png)$", n, re.I)), None)
            if name is None:
                raise LibraryError("this material has no colour map")
            info = z.getinfo(name)
            if info.file_size > MAX_IMAGE * 2:
                raise LibraryError("this material's colour map is too big")
            data = z.read(name)
    except zipfile.BadZipFile:
        raise LibraryError("ambientCG's download did not open") from None
    return data, {"item": iid, "from": f"https://ambientcg.com/a/{iid}", "map": "colour, 1K"}


def get(source: str, iid: str, kind: str) -> tuple[bytes, dict]:
    """(bytes, facts) of one library item. Raises LibraryError with a plain reason."""
    if source not in SOURCES or kind not in SOURCES[source]["kinds"]:
        raise LibraryError("this library has no such kind of item")
    if not ID.match(iid or ""):
        raise LibraryError("bad item id")
    if source == "kenney":
        return _kenney(iid)
    if source == "polyhaven":
        return _polyhaven_model(iid) if kind == "model" else _polyhaven_texture(iid)
    return _ambientcg_texture(iid)


# ---------------------------------------------------------------- into her project (a draft, like her own upload)
def add(tenant: str, ref: str, source: str, iid: str, kind: str = "model", key: str = "") -> dict[str, Any]:
    """One library item as a DRAFT asset of her Studio project. It is in the game only after she approves it."""
    from sqlalchemy import select
    from ..db import session
    from . import assets as A
    A.ensure_table()
    if kind not in KINDS:
        raise A.AssetError("kind = model | texture")
    r = A._studio(tenant, ref)
    try:
        data, facts = get(source, iid, kind)
    except LibraryError as e:
        raise A.AssetError(str(e)) from None
    key = A._clean_key(key or re.sub(r"^(platformer|city|fps|racing)_", "", iid.lower()), iid)
    src = SOURCES[source]
    meta = {"library": source, "licence": src["licence"], "credit": src["credit"], **facts}
    if kind == "model":
        try:
            fx = glbpack.facts(data)
        except glbpack.PackError as e:
            raise A.AssetError(f"the model is not a usable GLB: {e}") from None
        if fx["outside"]:
            raise A.AssetError("the model still needs files outside itself")
        meta.update(triangles=fx["triangles"], meshes=fx["meshes"], animations=fx["animations"])
    with session() as s:
        a = s.scalars(select(A.GameAsset).where(A.GameAsset.studio_id == r.id, A.GameAsset.key == key)).first()
        if a is None:
            n = len(s.scalars(select(A.GameAsset.id).where(A.GameAsset.studio_id == r.id)).all())
            if n >= A.MAX_ASSETS:
                raise A.AssetError(f"Is game mein {A.MAX_ASSETS} assets ho gaye.")
            a = A.GameAsset(tenant_id=tenant, studio_id=r.id, key=key, kind=kind, history=[],
                            words=f"{src['name']}: {facts.get('name') or iid}"[:600])
            s.add(a)
        elif a.kind != kind:
            raise A.AssetError(f"'{key}' is already a {a.kind}; give another name.")
        sp = A._spec(kind, {}, r)
        a.spec, a.status, a.cost_inr, a.error = sp, "making", 0.0, ""
        s.flush()
        aid = a.id
    if kind == "texture":
        png, more = A.make_image("texture", "", sp, A._bible(tenant, r.id), raw=data)
        return A._store(tenant, aid, png, "png", {**meta, **more, "model": None}, source=f"library:{source}")
    return A._store(tenant, aid, data, "glb", meta, source=f"library:{source}")


def status() -> dict[str, Any]:
    return {"sources": {k: {"name": v["name"], "licence": v["licence"], "kinds": list(v["kinds"]), "where": v["where"]}
                        for k, v in SOURCES.items()}, "kenney_on_disk": len(kenney_index())}
