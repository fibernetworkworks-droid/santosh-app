"""v0.543.0 P3 THE SCRAPE LANE - the zoom-grid ladder (docs/LEADS_PLAN.md sections 1.4 and 5.3).

One Google Maps search tops out around 120 results no matter how dense the area. The two published ways past it
(gosom's `-grid-bbox` cells, omkarcloud's Zoom 15-18 ladder) are the same idea: cut her area into cells at a
chosen zoom, one search per cell, and pick the zoom by MEASURED YIELD per cell - never by hope. This module is
the pure math half (the runner in service.py walks the cells it returns):

- `bbox_cells()`  - a square grid of cells covering the bbox of her sweep, at the zoom's cell size. Each cell
  records its own lat/lng/zoom/cell_km and (once the runner has been through it) its status, so a RESUME
  continues the GRID, not just the file (plan 5.5; the statuses live in the run's plan JSON, checkpointed
  after every cell).
- `choose_zoom()` - the ladder step, decided from the yields the run actually measured: a saturated area
  (median cells yielding ~full pages) steps FINER, a sparse area steps COARSER, and the card says which and
  why. Pure function over numbers - the "chosen by measured yield, never by hope" law, testable.

Non-overlapping cells on purpose: the Places lane tiles overlapping circles because Nearby silently drops
results past 20; the Maps public search returns locality-bound pages and the deduper (identity_key) collapses
whatever a seam shows twice. Overlap here would double the politeness spend for little yield.
"""
from __future__ import annotations

import math
from statistics import median

ZOOMS = (13, 14, 15, 16, 17)          # coarse -> fine; a zoom outside this is refused, not guessed
ZOOM_DEFAULT = 15
# the plan's default named: zoom 15 -> 1 km cells. The ladder is written, not derived - a later session can
# re-measure and re-write it, but it must do so HERE, loudly.
CELL_KM_BY_ZOOM = {13: 4.0, 14: 2.0, 15: 1.0, 16: 0.5, 17: 0.25}

SATURATED = 18                        # median yield/cell at or above this -> the area is dense, step finer
SPARSE = 2                            # median at or below this -> step coarser
MAX_CELLS = 400                       # the plan-time ceiling (config leads_scrape_max_cells; P1's places ceiling)


class GridError(ValueError):
    """A grid the plan refuses - the card names the number."""


def cell_km(zoom: int) -> float:
    z = int(zoom)
    if z not in CELL_KM_BY_ZOOM:
        raise GridError(f"Zoom {z} is not on the grid - ladder: {ZOOMS} (cell size {CELL_KM_BY_ZOOM}). "
                        f"Use one of these.")
    return CELL_KM_BY_ZOOM[z]


def bbox_cells(center: dict, sweep_km: float, zoom: int = ZOOM_DEFAULT,
               max_cells: int = MAX_CELLS) -> list[dict]:
    """Square cells covering the bbox of a `sweep_km` radius around the centre, at the zoom's cell size.
    i/j are the cell's grid coordinates (recorded so a resume names exactly where it stopped). Refused AT PLAN
    TIME past max_cells with the count named - never built into a run that then quietly stops halfway."""
    ck = cell_km(zoom)
    sweep_km = max(0.5, min(float(sweep_km or 3), 50.0))
    lat0, lng0 = float(center["lat"]), float(center["lng"])
    n = int(math.ceil(sweep_km / ck))                 # half-span in cells: -n..n covers +-sweep
    if (2 * n + 1) ** 2 > max_cells:
        raise GridError(f"This sweep makes {(2 * n + 1) ** 2} cells at zoom {zoom} - the ceiling for one run is "
                        f"{max_cells}. Reduce the sweep, change the zoom (finer cells), or run the city "
                        f"in parts. (Refused at plan time - never a silent truncate.)")
    step_lat = ck / 111.0
    step_lng = ck / max(0.2, math.cos(math.radians(lat0))) / 111.0
    cells: list[dict] = []
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            cells.append({"i": i, "j": j, "lat": round(lat0 + i * step_lat, 6), "lng": round(lng0 + j * step_lng, 6),
                          "zoom": int(zoom), "cell_km": ck, "status": "pending", "pages": 0, "found": 0,
                          "kept": 0, "duped": 0, "error": ""})
    return cells


def choose_zoom(yields: list[int], zoom: int) -> dict:
    """The ladder step from MEASURED yields (the run's per-cell found counts). Dense -> finer, sparse ->
    coarser, else stay. At a ladder edge the card says so instead of pretending a step happened."""
    ys = [int(y) for y in (yields or []) if y is not None] or [0]
    m = float(median(ys))
    z = int(zoom)
    idx = ZOOMS.index(z) if z in ZOOMS else ZOOMS.index(ZOOM_DEFAULT)
    if m >= SATURATED and idx < len(ZOOMS) - 1:
        return {"zoom": ZOOMS[idx + 1], "median_yield": m, "step": "finer",
                "why": f"the cells are dense (median {m:g} rows/cell >= {SATURATED}) - the next run takes finer cells at zoom "
                       f"{ZOOMS[idx + 1]}"}
    if m <= SPARSE and idx > 0:
        return {"zoom": ZOOMS[idx - 1], "median_yield": m, "step": "coarser",
                "why": f"the cells are sparse (median {m:g} rows/cell <= {SPARSE}) - the next run takes bigger cells at zoom "
                       f"{ZOOMS[idx - 1]}"}
    if m >= SATURATED:
        return {"zoom": z, "median_yield": m, "step": "finest",
                "why": f"median {m:g} rows/cell, but zoom {z} is already the finest - it cannot go finer"}
    if m <= SPARSE:
        return {"zoom": z, "median_yield": m, "step": "coarsest",
                "why": f"median {m:g} rows/cell, but zoom {z} is already the coarsest"}
    return {"zoom": z, "median_yield": m, "step": "stay",
            "why": f"median {m:g} rows/cell - zoom {z} fits well"}
