"""Google Maps Phase 9 APNA NAKSHA: HER OWN pins, lines and areas - on Hoola's server, drawn from Hoola's backend.

Why this exists (docs/research/maps/03_her_existing_map.md): there is NO API to write to a My Maps map and none to read or
write her saved lists. So she hands the data over ONCE - the KML/KMZ she exports from My Maps herself, or the file from
Google Takeout > Saved - and from then on Hoola owns it. Nothing here calls Google. It is HER data, so it is not Google
Maps Content and the Maps caching rules do not apply to it (stated assumption - Takeout is her own export).

* KML / KMZ is an open standard (OGC), parsed here; My Maps' own limits are the ceiling (KML/KMZ 5 MB).
* The Takeout "Saved" file's format is NOT documented anywhere Google publishes and third parties disagree
  (one CSV per list vs a single JSON), so the importer SNIFFS (GeoJSON / CSV) and REPORTS what it found; a row with no
  coordinates is kept as "no location" and is never geocoded behind her back (that would be a billed call, and Google's
  geocodes may only be kept 30 days). The first real export settles the format.
* To draw it: `GET /api/ownmap/{id}/geojson` returns a GeoJSON FeatureCollection for the Maps JS Data layer
  (`map.data.addGeoJson`), so her data never leaves her server. The drawing UI is NOT built here.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import zipfile
from datetime import datetime
from xml.etree import ElementTree as ET

from sqlalchemy import Float, Integer, String, Text, DateTime, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

MAX_MAPS = 20
MAX_FEATURES = 5000          # My Maps itself refuses imports over 2,000 rows; we allow a little more
MAX_FILE = 5 * 1024 * 1024   # My Maps' own KML/KMZ ceiling
MAX_UNZIPPED = 20 * 1024 * 1024
KINDS = ("point", "line", "polygon", "unlocated")


class OwnMapError(Exception):
    """The message is written for her."""


class OwnMap(Base):
    __tablename__ = "own_maps"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("om"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    source: Mapped[str] = mapped_column(String(16), default="manual")        # kml | takeout | manual
    detected: Mapped[str] = mapped_column(String(200), default="")           # what the sniffer found, in plain words
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OwnFeature(Base):
    __tablename__ = "own_features"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("of"))
    map_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    layer: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(12), default="point")
    name: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)           # the point, or the area's centre
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[str] = mapped_column(Text, default="")                  # GeoJSON geometry, '' for a plain point
    props: Mapped[str] = mapped_column(Text, default="{}")
    url: Mapped[str] = mapped_column(String(500), default="")                # a Maps link she saved (kept as text only)


_ready = False


def ensure_tables() -> None:
    """Self-heal (a database born before these models existed has no table)."""
    global _ready
    if _ready:
        return
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        OwnMap.__table__.create(eng, checkfirst=True)
        OwnFeature.__table__.create(eng, checkfirst=True)
    _ready = True


# ---------------------------------------------------------------- parsing
def _valid(lat: float, lng: float) -> bool:
    return -90 <= lat <= 90 and -180 <= lng <= 180 and not (lat == 0 and lng == 0)


def _coords(text: str) -> list[tuple[float, float]]:
    """KML coordinates are 'lon,lat[,alt]' pairs separated by whitespace - LONGITUDE first."""
    out = []
    for tok in (text or "").split():
        p = tok.split(",")
        try:
            lng, lat = float(p[0]), float(p[1])
        except (ValueError, IndexError):
            continue
        if _valid(lat, lng):
            out.append((lat, lng))
    return out


def _centre(pts: list[tuple[float, float]]) -> tuple[float, float]:
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _tag(el) -> str:
    return el.tag.rsplit("}", 1)[-1]


def _clean_text(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()[:2000]


def _read_kml_bytes(data: bytes, filename: str) -> bytes:
    if len(data) > MAX_FILE:
        raise OwnMapError("File 5 MB se badi hai (My Maps ki apni seema yehi hai). Chhoti karke dijiye.")
    if data[:2] == b"PK":                                   # KMZ = a zip holding doc.kml
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            raise OwnMapError("KMZ file kharab hai.")
        names = [i for i in z.infolist() if i.filename.lower().endswith(".kml")]
        if not names:
            raise OwnMapError("KMZ ke andar koi .kml nahi mili.")
        info = sorted(names, key=lambda i: (i.filename.lower() != "doc.kml", i.filename))[0]
        if info.file_size > MAX_UNZIPPED:
            raise OwnMapError("KMZ kholne par bahut badi ho jaati hai; import nahi kar sakta.")
        return z.read(info)
    return data


def parse_kml(data: bytes, filename: str = "") -> dict:
    raw = _read_kml_bytes(data, filename)
    head = raw[:4096].lower()
    if b"<!doctype" in raw[:20000].lower() or b"<!entity" in raw[:20000].lower():
        raise OwnMapError("Is KML mein DOCTYPE/ENTITY hai; suraksha ke liye import nahi karta.")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise OwnMapError(f"KML padh nahi paya ({str(e)[:60]}).")
    feats: list[dict] = []
    skipped = 0

    def walk(el, layer: str):
        nonlocal skipped
        for ch in list(el):
            t = _tag(ch)
            if t in ("Folder", "Document"):
                nm = next((_clean_text(c.text) for c in ch if _tag(c) == "name"), "")
                walk(ch, nm or layer)
            elif t == "Placemark":
                name = next((_clean_text(c.text) for c in ch if _tag(c) == "name"), "")
                note = next((_clean_text(c.text) for c in ch if _tag(c) == "description"), "")
                props = {}
                for d in ch.iter():
                    if _tag(d) == "Data" and d.get("name"):
                        v = next((_clean_text(c.text) for c in d if _tag(c) == "value"), "")
                        props[d.get("name")[:60]] = v[:300]
                geoms = []
                for g in ch.iter():
                    gt = _tag(g)
                    if gt == "Point":
                        c = _coords(next((x.text for x in g.iter() if _tag(x) == "coordinates"), ""))
                        if c:
                            geoms.append(("point", c[:1]))
                    elif gt == "LineString":
                        c = _coords(next((x.text for x in g.iter() if _tag(x) == "coordinates"), ""))
                        if len(c) >= 2:
                            geoms.append(("line", c))
                    elif gt == "Polygon":
                        ob = next((x for x in g.iter() if _tag(x) == "outerBoundaryIs"), None)
                        c = _coords(next((x.text for x in (ob.iter() if ob is not None else []) if _tag(x) == "coordinates"), ""))
                        if len(c) >= 3:
                            geoms.append(("polygon", c))
                if not geoms:
                    skipped += 1
                    continue
                for kind, pts in geoms:
                    lat, lng = pts[0] if kind == "point" else _centre(pts)
                    geom = ""
                    if kind == "line":
                        geom = json.dumps({"type": "LineString", "coordinates": [[p[1], p[0]] for p in pts]})
                    elif kind == "polygon":
                        ring = [[p[1], p[0]] for p in pts]
                        if ring[0] != ring[-1]:
                            ring.append(ring[0])
                        geom = json.dumps({"type": "Polygon", "coordinates": [ring]})
                    feats.append({"layer": layer, "kind": kind, "name": name, "note": note, "lat": lat, "lng": lng,
                                  "geometry": geom, "props": props, "url": ""})
    walk(root, "")
    return {"format": "kml/kmz", "features": feats, "skipped": skipped,
            "detected": f"KML/KMZ: {len(feats)} cheezein mili" + (f", {skipped} bina jagah ke chhodi" if skipped else "")}


def _first(d: dict, *keys: str):
    low = {str(k).strip().lower(): v for k, v in d.items()}
    for k in keys:
        if low.get(k) not in (None, ""):
            return low[k]
    return None


def parse_takeout(data: bytes, filename: str = "") -> dict:
    """Sniff, don't assume: GeoJSON (a FeatureCollection) or CSV. Says what it found; unknown shapes are refused
    rather than guessed at. A row with no coordinates becomes an 'unlocated' entry (kept, never geocoded here)."""
    if len(data) > 40 * 1024 * 1024:
        raise OwnMapError("File bahut badi hai.")
    text = data.decode("utf-8-sig", errors="replace")
    feats: list[dict] = []
    s = text.lstrip()
    if s[:1] in "{[":
        try:
            j = json.loads(text)
        except ValueError:
            raise OwnMapError("JSON padh nahi paya.")
        items = j.get("features") if isinstance(j, dict) else (j if isinstance(j, list) else None)
        if not isinstance(items, list):
            raise OwnMapError("Yeh JSON features ki list nahi hai - is shape ko main pehchanta nahi (andaza nahi lagaunga).")
        for it in items:
            if not isinstance(it, dict):
                continue
            props = it.get("properties") if isinstance(it.get("properties"), dict) else {}
            loc = props.get("Location") if isinstance(props.get("Location"), dict) else {}
            geo = it.get("geometry") if isinstance(it.get("geometry"), dict) else {}
            lat = lng = None
            c = geo.get("coordinates")
            if geo.get("type") == "Point" and isinstance(c, list) and len(c) >= 2:
                lng, lat = c[0], c[1]
            gc = loc.get("Geo Coordinates") if isinstance(loc.get("Geo Coordinates"), dict) else {}
            if lat in (None, "", 0) and gc:
                lat, lng = gc.get("Latitude"), gc.get("Longitude")
            title = _first(props, "title", "name") or loc.get("Business Name") or ""
            url = _first(props, "google maps url", "url") or ""
            note = " ".join(str(x) for x in (_first(props, "comment", "note"), loc.get("Address")) if x)
            feats.append(_saved_row(title, note, url, lat, lng))
        fmt = "GeoJSON/JSON"
    else:
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rdr = csv.DictReader(io.StringIO(text), dialect=dialect)
        cols = [c for c in (rdr.fieldnames or []) if c]
        if not cols:
            raise OwnMapError("CSV mein columns nahi mile.")
        for row in rdr:
            lat = _first(row, "latitude", "lat", "y")
            lng = _first(row, "longitude", "lng", "lon", "long", "x")
            feats.append(_saved_row(_first(row, "title", "name") or "", _first(row, "note", "comment", "notes") or "",
                                    _first(row, "url", "google maps url", "link") or "", lat, lng))
        fmt = "CSV (columns: " + ", ".join(cols[:8]) + ")"
    feats = [f for f in feats if f["name"] or f["url"] or f["lat"] is not None]
    nloc = sum(1 for f in feats if f["lat"] is not None)
    return {"format": fmt, "features": feats, "skipped": 0,
            "detected": f"{fmt}: {len(feats)} rows, {nloc} mein jagah (coordinates), {len(feats) - nloc} bina jagah ke"}


def _saved_row(title, note, url, lat, lng) -> dict:
    try:
        la, lo = float(lat), float(lng)
        ok = _valid(la, lo)
    except (TypeError, ValueError):
        la = lo = 0.0
        ok = False
    return {"layer": "", "kind": "point" if ok else "unlocated", "name": _clean_text(str(title))[:200],
            "note": _clean_text(str(note))[:2000], "lat": la if ok else None, "lng": lo if ok else None,
            "geometry": "", "props": {}, "url": str(url or "")[:500]}


# ---------------------------------------------------------------- storage + queries
def import_file(tenant: str, data: bytes, filename: str, name: str = "", kind: str = "auto") -> dict:
    ensure_tables()
    low = (filename or "").lower()
    is_kml = low.endswith((".kml", ".kmz")) or data[:2] == b"PK" or b"<kml" in data[:2000].lower()
    parsed = parse_kml(data, filename) if (kind == "kml" or (kind == "auto" and is_kml)) else parse_takeout(data, filename)
    feats = parsed["features"]
    if not feats:
        raise OwnMapError("File mein koi jagah/entry nahi mili. " + parsed["detected"])
    if len(feats) > MAX_FEATURES:
        raise OwnMapError(f"{len(feats)} entries hain; ek map mein {MAX_FEATURES} tak. File do hisson mein baant dein.")
    with session() as s:
        if len(s.scalars(select(OwnMap).where(OwnMap.tenant_id == tenant)).all()) >= MAX_MAPS:
            raise OwnMapError(f"{MAX_MAPS} map ho chuke; pehle koi hatayiye.")
        m = OwnMap(tenant_id=tenant, name=(name or filename or "Mera map")[:120],
                   source="kml" if parsed["format"].startswith("kml") else "takeout", detected=parsed["detected"][:200])
        s.add(m)
        s.flush()
        for f in feats:
            s.add(OwnFeature(map_id=m.id, tenant_id=tenant, layer=f["layer"][:120], kind=f["kind"], name=f["name"],
                             note=f["note"], lat=f["lat"], lng=f["lng"], geometry=f["geometry"],
                             props=json.dumps(f["props"]), url=f["url"]))
        kinds: dict[str, int] = {}
        for f in feats:
            kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
        return {"map": m.id, "name": m.name, "detected": parsed["detected"], "count": len(feats), "kinds": kinds,
                "layers": sorted({f["layer"] for f in feats if f["layer"]})[:20], "skipped": parsed["skipped"]}


def maps(tenant: str) -> list[dict]:
    ensure_tables()
    with session() as s:
        out = []
        for m in s.scalars(select(OwnMap).where(OwnMap.tenant_id == tenant).order_by(OwnMap.created_at.desc())).all():
            n = len(s.scalars(select(OwnFeature.id).where(OwnFeature.map_id == m.id)).all())
            out.append({"map": m.id, "name": m.name, "source": m.source, "detected": m.detected, "count": n})
        return out


def _own(s, tenant: str, map_id: str) -> OwnMap:
    m = s.get(OwnMap, map_id)
    if m is None or m.tenant_id != tenant:                 # another tenant's map is "not found", never "forbidden"
        raise OwnMapError("Yeh map nahi mila.")
    return m


def geojson(tenant: str, map_id: str) -> dict:
    """A FeatureCollection for the Maps JS Data layer (map.data.addGeoJson). 'unlocated' rows are left out - they
    have nothing to draw."""
    ensure_tables()
    with session() as s:
        m = _own(s, tenant, map_id)
        feats = []
        for f in s.scalars(select(OwnFeature).where(OwnFeature.map_id == m.id, OwnFeature.kind != "unlocated")).all():
            geom = json.loads(f.geometry) if f.geometry else {"type": "Point", "coordinates": [f.lng, f.lat]}
            feats.append({"type": "Feature", "id": f.id, "geometry": geom,
                          "properties": {"name": f.name, "note": f.note, "layer": f.layer, **json.loads(f.props or "{}")}})
        return {"type": "FeatureCollection", "name": m.name, "features": feats}


def _km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    la1, la2 = math.radians(a_lat), math.radians(b_lat)
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(math.radians(b_lng - a_lng) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def near(tenant: str, lat: float, lng: float, radius_km: float = 5, map_id: str = "", limit: int = 20) -> list[dict]:
    """Her own places within a radius, by straight-line distance - pure arithmetic, no Google call, no cost."""
    ensure_tables()
    with session() as s:
        q = select(OwnFeature).where(OwnFeature.tenant_id == tenant, OwnFeature.lat.is_not(None))
        if map_id:
            _own(s, tenant, map_id)
            q = q.where(OwnFeature.map_id == map_id)
        rows = []
        for f in s.scalars(q).all():
            d = _km(lat, lng, f.lat, f.lng)
            if d <= radius_km:
                rows.append({"name": f.name, "layer": f.layer, "kind": f.kind, "note": f.note, "lat": f.lat, "lng": f.lng,
                             "distance_km": round(d, 2), "map": f.map_id})
        rows.sort(key=lambda r: r["distance_km"])
        return rows[:max(1, min(int(limit), 100))]


def add_pin(tenant: str, map_id: str, name: str, lat: float, lng: float, note: str = "") -> dict:
    ensure_tables()
    if not _valid(float(lat), float(lng)):
        raise OwnMapError("lat/lng sahi nahi hain.")
    with session() as s:
        m = _own(s, tenant, map_id)
        n = len(s.scalars(select(OwnFeature.id).where(OwnFeature.map_id == m.id)).all())
        if n >= MAX_FEATURES:
            raise OwnMapError(f"Is map mein {MAX_FEATURES} se zyada entries nahi ho sakti.")
        f = OwnFeature(map_id=m.id, tenant_id=tenant, kind="point", name=str(name or "")[:200], note=str(note or "")[:2000],
                       lat=float(lat), lng=float(lng))
        s.add(f)
        s.flush()
        return {"id": f.id, "map": m.id, "name": f.name}


def delete_map(tenant: str, map_id: str) -> dict:
    ensure_tables()
    with session() as s:
        m = _own(s, tenant, map_id)
        n = 0
        for f in s.scalars(select(OwnFeature).where(OwnFeature.map_id == m.id)).all():
            s.delete(f)
            n += 1
        s.delete(m)
        return {"deleted": m.name, "entries": n}
