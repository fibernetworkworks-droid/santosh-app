"""v0.343 DESIGN SE MILAAN (App Sahayak Phase 10, owner: "START PHASE 10"): the real app screens are compared with HER
APPROVED DESIGN - the open promise of the original Phase 3 ("screenshots are compared against the approved design").

After every Android / iPhone build the device check's screenshot of each screen is scored against the approved design's
screenshot of the same screen on the same platform (`score`, numbers only, free): a colour score (palette histograms) and a
layout score (where the ink sits: edge maps compared block by block), 0-100. On her ask ("design se milao") Opus LOOKS at
both pictures of every screen under MATCH_MIN and writes the concrete visible differences; with fix=True those screens are
rebuilt with the differences as their notes (Android `build(only, notes)`, iPhone the same) - the rest of the app is kept.
Kit screens (sign-in, account, inbox) have no design to match and are skipped."""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

from ..db import now, session
from . import kit as K
from . import service as AS
from .models import AppProject

log = logging.getLogger("santosh.appmaker")
MATCH_MIN = 70                 # a screen under this (0-100) is looked at by Opus and offered a rebuild
W, H = 60, 130                 # the comparison grid (portrait phone)

DIFF_SYSTEM = """You compare TWO screenshots of the same app screen: image 1 = the APPROVED DESIGN (what the owner signed
off), image 2 = the REAL NATIVE APP screen ({platform}) built from it. List the concrete VISIBLE differences that make the
native screen not look like the design - missing or extra sections, wrong order, wrong colours (backgrounds, buttons, text),
wrong sizes / weights of headings, missing pictures or icons, different card shapes / spacing, different button style. Ignore:
the phone status bar, real data vs sample data (different names / numbers), small font rendering differences, a system
navigation bar. Return JSON {"score": 0-10 (10 = looks the same), "differences": ["short imperative fix", ...max 6]}.
Each difference is an instruction a developer can follow ("Put the offers carousel above the categories", "Buttons are
pill-shaped and violet in the design, not square grey")."""


def _img(b: bytes, trim_top: float = 0.0):
    from PIL import Image
    im = Image.open(io.BytesIO(b)).convert("RGB")
    if trim_top:
        w, h = im.size
        im = im.crop((0, int(h * trim_top), w, h))
    return im


def score(design: bytes, native: bytes) -> dict[str, int]:
    """0-100 colour + layout likeness of a native screenshot to the design one (status bar trimmed off the native)."""
    import numpy as np
    from PIL import ImageFilter
    a = _img(design)
    b = _img(native, trim_top=0.045)
    # colour: 4x4x4 palette histograms, intersection
    def hist(im):
        q = np.asarray(im.resize((W, H)), dtype=np.int32) // 64
        idx = q[..., 0] * 16 + q[..., 1] * 4 + q[..., 2]
        h = np.bincount(idx.ravel(), minlength=64).astype(float)
        return h / h.sum()
    colour = float(np.minimum(hist(a), hist(b)).sum())
    # layout: edge maps on the grid, compared as blocks of ink (where things are), correlation -> 0..1
    def edges(im):
        e = np.asarray(im.convert("L").filter(ImageFilter.FIND_EDGES).resize((W, H)), dtype=float)
        blocks = e.reshape(H // 10, 10, W // 10, 10).mean(axis=(1, 3))
        return blocks.ravel()
    ea, eb = edges(a), edges(b)
    if ea.std() < 1e-6 or eb.std() < 1e-6:
        layout = 0.0
    else:
        layout = max(0.0, float(np.corrcoef(ea, eb)[0, 1]))
    # light vs dark: a whole-screen brightness clash is a big miss even when the palette overlaps
    la = float(np.asarray(a.convert("L")).mean())
    lb = float(np.asarray(b.convert("L")).mean())
    bright = 1.0 - min(1.0, abs(la - lb) / 128.0)
    total = 0.4 * colour + 0.45 * layout + 0.15 * bright
    return {"score": round(total * 100), "colour": round(colour * 100), "layout": round(layout * 100), "light": round(bright * 100)}


def _design_shot(r: AppProject, sid: str, platform: str) -> Path | None:
    d = K.app_dir(r.tenant_id, r.id) / "shots"
    for name in (f"{sid}-{platform}.jpg", f"{sid}-android.jpg"):
        if (d / name).exists():
            return d / name
    return None


def _native_dir(r: AppProject, platform: str) -> tuple[Path | None, dict[str, Any]]:
    from .android import service as AN
    from .ios import service as IO
    st = AN.state(r) if platform == "android" else IO.state(r)
    qa = st.get("qa") or {}
    if not qa.get("ran") or not qa.get("build"):
        return None, st
    base = AN._dir(r) if platform == "android" else IO._dir(r)
    return base / "qa" / f"b{qa['build']}", st


def _ids(r: AppProject) -> list[str]:
    return [s for s in AS._j(r.plan, {}).get("screens", [])]


def score_all(r: AppProject, platform: str) -> dict[str, Any]:
    """Numbers only (no model): every designed screen that has both pictures. Kept in the app state."""
    folder, st = _native_dir(r, platform)
    out: dict[str, Any] = {}
    if folder is None or not folder.exists():
        return out
    for sid in _ids(r):
        d, n = _design_shot(r, sid, platform), folder / f"{sid}.png"
        if d is None or not n.exists():
            continue
        try:
            out[sid] = score(d.read_bytes(), n.read_bytes())
        except Exception:                              # noqa: BLE001  a broken picture is skipped, never a guess
            log.info("match %s %s skipped", sid, platform, exc_info=True)
    if out:
        _keep(r, platform, {"build": (st.get("qa") or {}).get("build"), "at": now().isoformat(), "screens": out,
                            "avg": round(sum(x["score"] for x in out.values()) / len(out))})
    return out


def _keep(r: AppProject, platform: str, data: dict[str, Any]) -> None:
    from .android import service as AN
    cur = dict(AN.state(AS._load(r.id)).get("match") or {})
    old = cur.get(platform) or {}
    # Opus's notes stay with a screen until a build changes it (same build -> keep them)
    if old.get("build") == data.get("build"):
        for sid, x in (old.get("screens") or {}).items():
            if sid in data["screens"] and x.get("differences"):
                data["screens"][sid]["differences"] = x["differences"]
                data["screens"][sid]["opus"] = x.get("opus")
    cur[platform] = data
    AN._put(r.id, match=cur)


def after_build(r: AppProject, platform: str) -> None:
    """Called at the end of a build: the numbers for the card (never fails the build)."""
    try:
        score_all(AS._load(r.id), platform)
    except Exception:                                  # noqa: BLE001
        log.info("design match after build skipped", exc_info=True)


def check(tenant: str, ref: str, platform: str = "android", fix: bool = False, conv: str = "") -> dict[str, Any]:
    """Her ask: score every screen, Opus looks at the ones under MATCH_MIN and lists the differences; fix=True rebuilds
    those screens with the differences as notes (the rest of the app is kept)."""
    if platform not in ("android", "ios"):
        raise AS.AppError("platform: android or ios")
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    scores = score_all(r, platform)
    if not scores:
        raise AS.AppError(("Android" if platform == "android" else "iPhone") + " app has no device-check screenshots yet: "
                          "let the app be built first (with the device check on the build machine).")
    folder, _st = _native_dir(r, platform)
    low = sorted((sid for sid, x in scores.items() if x["score"] < MATCH_MIN), key=lambda s: scores[s]["score"])[:8]
    from ..site import ai as SA
    labels = AS._j(r.plan, {}).get("labels") or {}
    for sid in low:
        d = _design_shot(r, sid, platform)
        try:
            got = SA.ask_json(DIFF_SYSTEM.replace("{platform}", "Android" if platform == "android" else "iPhone"),
                              f"SCREEN: {labels.get(sid, sid)} ({sid}). Image 1 = design, image 2 = native app.", 1500, "app_edit",
                              images=[d.read_bytes(), (folder / f"{sid}.png").read_bytes()])
        except Exception as e:                         # noqa: BLE001
            if isinstance(e, SA.AiError):
                raise AS.AppError(str(e)) from e
            log.info("match diff %s failed", sid, exc_info=True)
            continue
        diffs = [str(x)[:200] for x in (got or {}).get("differences") or [] if str(x).strip()][:6]
        scores[sid]["differences"] = diffs
        try:
            scores[sid]["opus"] = max(0, min(10, int(float((got or {}).get("score") or 0))))
        except (TypeError, ValueError):
            scores[sid]["opus"] = None
    from .android import service as AN
    cur = dict(AN.state(AS._load(r.id)).get("match") or {})
    cur[platform] = {**(cur.get(platform) or {}), "screens": scores, "checked": now().isoformat()}
    AN._put(r.id, match=cur)
    rebuilt: list[str] = []
    if fix:
        notes = {sid: "MAKE THIS SCREEN LOOK LIKE ITS APPROVED DESIGN. The last build differed visibly:\n- "
                 + "\n- ".join(scores[sid]["differences"]) for sid in low if scores[sid].get("differences")}
        if notes:
            if platform == "android":
                AN.build(tenant, r.id, conv or r.conv, list(notes), notes)
            else:
                from .ios import service as IO
                IO.build(tenant, r.id, conv or r.conv, "sim", list(notes), notes)
            rebuilt = list(notes)
    return view(AS._load(r.id), platform) | {"rebuilt": rebuilt,
                                             "say": (f"{len(low)} screens match the design poorly; " + (f"{len(rebuilt)} are being rebuilt." if rebuilt
                                                     else "the differences are on the card.")) if low else "All screens match the design."}


def view(r: AppProject, platform: str = "") -> dict[str, Any]:
    from .android import service as AN
    m = AN.state(r).get("match") or {}
    labels = AS._j(r.plan, {}).get("labels") or {}
    out = {}
    for plat in ([platform] if platform else ["android", "ios"]):
        x = m.get(plat) or {}
        rows = []
        for sid, v in (x.get("screens") or {}).items():
            d = _design_shot(r, sid, plat)
            rows.append({"id": sid, "label": labels.get(sid, sid), **v, "design": d.name if d else ""})
        rows.sort(key=lambda z: z["score"])
        out[plat] = {"build": x.get("build"), "avg": x.get("avg"), "at": x.get("at"), "checked": x.get("checked"), "min": MATCH_MIN,
                     "screens": rows}
    return {"match": out}


def get(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    return view(r)
