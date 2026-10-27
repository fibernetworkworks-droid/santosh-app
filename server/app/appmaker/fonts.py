"""v0.128.1 Fonts for apps: 315 open-licence families (OFL / Apache / UFL, from Fontsource on npm) incl. every major Indian
script (Devanagari, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Gurmukhi, Odia) plus Urdu / Arabic and CJK.
The catalogue (`fontcat.json`, built by tool/apps/font_catalog.py) is shipped; the font FILES are fetched on first use
from the official npm registry tarball (sha512 integrity checked) into data/app_fonts/ and reused. The 36 website fonts
already bundled are used directly. 80 font pairs (head / body / script font) are offered; she can also name any family."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import re
import tarfile
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..site import build as SB
from ..site import taxonomy as ST

log = logging.getLogger("santosh.app")
CAT = Path(__file__).resolve().parent / "fontcat.json"
REGISTRY = "https://registry.npmjs.org/"
MAX_TARBALL = 220 * 1024 * 1024
_LOCK = threading.Lock()

SCRIPT_OF_LANG = {"hi": "devanagari", "mr": "devanagari", "ne": "devanagari", "sa": "devanagari", "bn": "bengali", "as": "bengali",
                  "ta": "tamil", "te": "telugu", "kn": "kannada", "ml": "malayalam", "gu": "gujarati", "pa": "gurmukhi",
                  "or": "oriya", "ur": "arabic"}
SCRIPT_RANGES = {"devanagari": "U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+20B9,U+25CC,U+A830-A839,U+A8E0-A8FF",
                 "bengali": "U+0951-0952,U+0964-0965,U+0980-09FE,U+1CD0,U+200C-200D,U+20B9,U+25CC",
                 "tamil": "U+0964-0965,U+0B82-0BFA,U+200C-200D,U+20B9,U+25CC", "telugu": "U+0951-0952,U+0964-0965,U+0C00-0C7F,U+200C-200D,U+25CC",
                 "kannada": "U+0951-0952,U+0964-0965,U+0C80-0CF3,U+200C-200D,U+20B9,U+25CC",
                 "malayalam": "U+0307,U+0323,U+0951-0952,U+0964-0965,U+0D00-0D7F,U+200C-200D,U+20B9,U+25CC",
                 "gujarati": "U+0951-0952,U+0964-0965,U+0A80-0AFF,U+200C-200D,U+20B9,U+25CC,U+A830-A839",
                 "gurmukhi": "U+0951-0952,U+0964-0965,U+0A01-0A76,U+200C-200D,U+20B9,U+25CC,U+262C",
                 "oriya": "U+0951-0952,U+0964-0965,U+0B01-0B77,U+200C-200D,U+20B9,U+25CC",
                 "arabic": "U+0600-06FF,U+0750-077F,U+0870-088E,U+0890-0891,U+0897-08E1,U+08E3-08FF,U+200C-200E,U+FB50-FDFF,U+FE70-FE74,U+FE76-FEFC"}
SCRIPT_DEFAULT = {"devanagari": "Mukta", "bengali": "Hind Siliguri", "tamil": "Mukta Malar", "telugu": "Noto Sans Telugu",
                  "kannada": "Noto Sans Kannada", "malayalam": "Noto Sans Malayalam", "gujarati": "Mukta Vaani",
                  "gurmukhi": "Mukta Mahee", "oriya": "Noto Sans Oriya", "arabic": "Noto Naskh Arabic"}

# 50 more pairs on top of the website's 30 (head, body, devanagari)
EXTRA_PAIRS = {
    "lexend_mukta": ("Lexend", "Lexend", "Mukta"), "figtree_hind": ("Figtree", "Figtree", "Hind"),
    "onest_mukta": ("Onest", "Onest", "Mukta"), "unbounded_inter": ("Unbounded", "Inter", "Mukta"),
    "gabarito_inter": ("Gabarito", "Inter", "Mukta"), "schibsted_inter": ("Schibsted Grotesk", "Inter", "Mukta"),
    "hanken_hind": ("Hanken Grotesk", "Hanken Grotesk", "Hind"), "redhat_mukta": ("Red Hat Display", "Red Hat Text", "Mukta"),
    "albert_mukta": ("Albert Sans", "Albert Sans", "Mukta"), "epilogue_inter": ("Epilogue", "Inter", "Mukta"),
    "vietnam_hind": ("Be Vietnam Pro", "Be Vietnam Pro", "Hind"), "intertight_inter": ("Inter Tight", "Inter", "Mukta"),
    "montserrat_hind": ("Montserrat", "Hind", "Hind"), "raleway_lato": ("Raleway", "Lato", "Martel"),
    "rubik_mukta": ("Rubik", "Rubik", "Mukta"), "worksans_hind": ("Work Sans", "Work Sans", "Hind"),
    "karla_mukta": ("Karla", "Karla", "Mukta"), "barlow_mukta": ("Barlow", "Barlow", "Mukta"),
    "bebas_inter": ("Bebas Neue", "Inter", "Teko"), "oswald_hind": ("Oswald", "Hind", "Khand"),
    "anton_inter": ("Anton", "Inter", "Teko"), "fredoka_nunito": ("Fredoka", "Nunito", "Baloo 2"),
    "quicksand_nunito": ("Quicksand", "Nunito", "Baloo 2"), "comfortaa_mukta": ("Comfortaa", "Nunito", "Baloo 2"),
    "lilita_nunito": ("Lilita One", "Nunito", "Baloo 2"), "bungee_inter": ("Bungee", "Inter", "Baloo 2"),
    "chewy_nunito": ("Chewy", "Nunito", "Baloo 2"), "merriweather_sans": ("Merriweather", "Merriweather Sans", "Martel"),
    "librebask_source": ("Libre Baskerville", "Source Sans 3", "Tiro Devanagari Hindi"),
    "ebgaramond_inter": ("EB Garamond", "Inter", "Tiro Devanagari Hindi"), "crimson_inter": ("Crimson Pro", "Inter", "Martel"),
    "bodoni_manrope": ("Bodoni Moda", "Manrope", "Martel"), "cinzel_lato": ("Cinzel", "Lato", "Martel"),
    "marcellus_lato": ("Marcellus", "Lato", "Martel"), "prata_inter": ("Prata", "Inter", "Martel"),
    "yeseva_lato": ("Yeseva One", "Lato", "Rozha One"), "youngserif_inter": ("Young Serif", "Inter", "Martel"),
    "gloock_inter": ("Gloock", "Inter", "Rozha One"), "zilla_inter": ("Zilla Slab", "Inter", "Martel"),
    "robotoslab_roboto": ("Roboto Slab", "Roboto", "Mukta"), "bitter_source": ("Bitter", "Source Sans 3", "Martel"),
    "plexsans_plexdeva": ("IBM Plex Sans", "IBM Plex Sans", "IBM Plex Sans Devanagari"),
    "plexserif_plexsans": ("IBM Plex Serif", "IBM Plex Sans", "IBM Plex Sans Devanagari"),
    "jetbrains_inter": ("JetBrains Mono", "Inter", "Mukta"), "spacemono_inter": ("Space Mono", "Inter", "Mukta"),
    "atkinson_hind": ("Atkinson Hyperlegible", "Atkinson Hyperlegible", "Hind"),
    "notosans_notodeva": ("Noto Sans", "Noto Sans", "Noto Sans Devanagari"),
    "notoserif_notoserifdeva": ("Noto Serif", "Noto Sans", "Noto Serif Devanagari"),
    "akshar_hind": ("Akshar", "Hind", "Akshar"), "anek_anekdeva": ("Anek Latin", "Anek Latin", "Anek Devanagari"),
}


@lru_cache(maxsize=1)
def catalog() -> dict[str, dict[str, Any]]:
    try:
        return json.loads(CAT.read_text())
    except (OSError, ValueError):
        return {}


def slug(fam: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (fam or "").lower()).strip("-")


def pairs() -> dict[str, dict[str, str]]:
    out = {k: dict(v) for k, v in ST.FONTS.items()}
    for k, (h, b, d) in EXTRA_PAIRS.items():
        out[k] = {"head": h, "body": b, "deva": d}
    return out


def find(name: str) -> dict[str, Any] | None:
    """A family by (rough) name: 'poppins', 'Noto Sans Tamil', 'baloo'."""
    c = catalog()
    s = slug(name)
    if s in c:
        return c[s]
    for rec in c.values():
        if slug(rec["family"]) == s:
            return rec
    hits = [r for r in c.values() if s and s in r["id"]]
    return sorted(hits, key=lambda r: len(r["id"]))[0] if hits else None


def families(script: str = "", category: str = "", q: str = "") -> list[dict[str, Any]]:
    out = []
    for r in catalog().values():
        if script and script not in r["subsets"]:
            continue
        if category and r["category"] != category:
            continue
        if q and slug(q) not in r["id"]:
            continue
        out.append({k: r[k] for k in ("id", "family", "category", "subsets", "weights", "license")})
    return out


def counts() -> dict[str, int]:
    c = catalog()
    return {"families": len(c), "pairs": len(pairs()),
            **{f"script_{s}": sum(1 for r in c.values() if s in r["subsets"]) for s in SCRIPT_DEFAULT}}


def _dir() -> Path:
    p = Path(os.environ.get("APP_FONTS_DIR", "data/app_fonts"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _fetch_ok() -> bool:
    return os.environ.get("APP_FONTS_FETCH", "true").lower() not in ("0", "false", "off", "no")


def _download(rec: dict[str, Any]) -> bytes:
    import httpx
    url = rec["tarball"]
    if not url.startswith(REGISTRY):
        raise ValueError("font tarball not on the npm registry")
    with httpx.Client(timeout=120, follow_redirects=False) as c:
        r = c.get(url)
        r.raise_for_status()
        data = r.content
    if len(data) > MAX_TARBALL:
        raise ValueError("font package too big")
    algo, _, want = rec["integrity"].partition("-")
    if algo != "sha512" or base64.b64encode(hashlib.sha512(data).digest()).decode() != want:
        raise ValueError("font package integrity mismatch")
    return data


def ensure(family: str, subsets: tuple[str, ...] = ("latin",), weights: tuple[int, ...] = (400, 700)) -> list[tuple[str, int, Path]]:
    """[(subset, weight, file)] for a family: bundled website files first, else the cached / downloaded npm files."""
    out: list[tuple[str, int, Path]] = []
    sl = slug(family)
    for sub in subsets:
        for w in weights:
            f = SB.ASSETS / "fonts" / f"{sl}-{sub}-{w}.woff2"
            if f.exists():
                out.append((sub, w, f))
    if len(out) == len(subsets) * len(weights):
        return out
    rec = find(family)
    if not rec:
        return out
    have = {(s, w) for s, w, _ in out}
    d = _dir() / rec["id"]
    need = [(s, w) for s in subsets if s in rec["subsets"] for w in weights if (s, w) not in have]
    missing = [(s, w) for s, w in need if not (d / f"{rec['id']}-{s}-{w}.woff2").exists()]
    if missing and _fetch_ok():
        with _LOCK:
            try:
                data = _download(rec)
                d.mkdir(parents=True, exist_ok=True)
                with tarfile.open(fileobj=io.BytesIO(data)) as tf:
                    names = {m.name.split("/")[-1]: m for m in tf.getmembers() if m.name.endswith("-normal.woff2")}
                    for s, w in missing:
                        ws = sorted(rec["weights"], key=lambda x: abs(x - w)) or [w]
                        for cand in ws:
                            m = names.get(f"{rec['id']}-{s}-{cand}-normal.woff2")
                            if m:
                                blob = tf.extractfile(m).read()
                                if blob[:4] == b"wOF2":
                                    (d / f"{rec['id']}-{s}-{w}.woff2").write_bytes(blob)
                                break
            except Exception as e:
                log.info("font %s not fetched: %s", family, e)
    for s, w in need:
        f = d / f"{rec['id']}-{s}-{w}.woff2"
        if f.exists():
            out.append((s, w, f))
    return out


def face_css(files: list[tuple[str, str, int, str]]) -> str:
    """[(family, subset, weight, url)] -> @font-face rules with unicode ranges per script."""
    out = []
    for fam, sub, w, url in files:
        rng = f"unicode-range:{SCRIPT_RANGES[sub]};" if sub in SCRIPT_RANGES else ""
        out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:normal;font-display:swap;{rng}src:url({url}) format('woff2')}}")
    return "\n".join(out)
