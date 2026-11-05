"""v0.538 SPEED (web Step 6, W10): the parts of "fast on a mid phone" that code can guarantee on every build.

  * precompress(out): every text file (html / css / js / json / xml / svg / txt) of 1 KB or more gets a gzip twin
    (`page.html.gz`, level 9, fixed mtime so a rebuild with the same content is byte-identical). nginx serves the twin
    with `gzip_static on` (edge.nginx_conf) - no compression work per visitor, which is what keeps 10,000 product pages
    cheap to serve; a CDN in front caches the same bytes.
  * budget(out): every page's HTML size against HTML_BUDGET (100 KB, the plan's target). The browser checks
    (checks.py) measure LCP and CLS on a 4x-slowed phone CPU for the pages they open; this covers EVERY page.
"""
from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any

TEXT = {".html", ".css", ".js", ".json", ".xml", ".svg", ".txt", ".webmanifest"}
MIN_BYTES = 1024
HTML_BUDGET = 100 * 1024
STATS = {"files": 0, "saved": 0}


def precompress(out: Path) -> dict[str, int]:
    n = saved = 0
    for p in out.rglob("*"):
        if not p.is_file() or p.suffix not in TEXT:
            continue
        raw = p.read_bytes()
        if len(raw) < MIN_BYTES:
            continue
        gz = gzip.compress(raw, compresslevel=9, mtime=0)
        if len(gz) >= len(raw):
            continue
        (p.parent / (p.name + ".gz")).write_bytes(gz)
        n += 1
        saved += len(raw) - len(gz)
    STATS["files"] += n
    STATS["saved"] += saved
    return {"files": n, "saved": saved}


def budget(out: Path, limit: int = HTML_BUDGET) -> dict[str, Any]:
    """Every page over the HTML budget (biggest first) + the biggest page."""
    sizes = [(p.stat().st_size, p.relative_to(out).parent.as_posix() or "home") for p in out.rglob("index.html")]
    over = sorted([x for x in sizes if x[0] > limit], reverse=True)
    top = max(sizes) if sizes else (0, "")
    return {"pages": len(sizes), "over": [{"page": pg, "kb": round(b / 1024, 1)} for b, pg in over[:20]],
            "over_count": len(over), "max_kb": round(top[0] / 1024, 1), "max_page": top[1], "limit_kb": limit // 1024}
